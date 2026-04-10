# Speaker Identification Playbook

Three-stage flow for identifying and mapping speakers in transcripts. Applies to all pathways but most critical for P2 (diarization-based).

## Stage 1: Metadata Research

**Goal:** Extract speaker information from video/audio metadata without listening.

**Input:** YouTube title, description, channel name, or file metadata tags.

**Process:**

1. **Initialize LLM prompt with GPT-4o-mini** — Use fast model for speed and cost (not gpt-4).

2. **Structured extraction** — Ask model to extract speaker roles from title + description only. Provide strict output schema:
   ```json
   {
     "host": "Name or null",
     "co_host": "Name or null or list of names",
     "guests": ["Name1", "Name2"] or [],
     "confidence": 0.0 to 1.0,
     "evidence": "Direct quotes from title/description or reasoning"
   }
   ```

3. **Example prompt:**
   ```
   Extract speaker roles from the following metadata. Return ONLY JSON.
   
   Title: "Regenerative Finance with Gregory Landua & Monty Bryant"
   Description: "In this episode, host Sarah Chen interviews..."
   
   Rules:
   - Host: primary speaker, usually mentioned first or explicitly called "host"
   - Co-host: regular co-presenter (if title says "with X & Y", both may be co-hosts)
   - Guests: one-time or occasional speakers
   - Return null if role cannot be determined
   - Confidence: how certain you are (0.0 = pure guess, 1.0 = stated explicitly)
   
   Return: {"host": "...", "co_host": "...", "guests": [...], "confidence": ..., "evidence": "..."}
   ```

4. **Accept metadata results if confidence > 0.7** — If model confident, use result as prior.

**Output:** `metadata_speakers: {host, co_host, guests, confidence}`

---

## Stage 2: LLM Transcript Guess

**Goal:** Use the actual transcript to infer speaker roles without manual listening.

**Input:** Transcript text (first ~8000 tokens max), title, description.

**Process:**

1. **Feed limited transcript** — Use only the **first 8000 tokens** of the transcript (roughly 5–10 minutes of speech). This keeps LLM cost low and focuses on speaker introduction/context.

2. **Strict inference rules** — Prompt GPT-4o-mini with CRITICAL rules:
   ```
   CRITICAL RULES for speaker identification:
   1. ONLY use direct evidence: self-introduction ("I'm Gregory"), 
      or direct address ("Sarah, tell us about...")
   2. NEVER assume first speaker is the host
   3. NEVER assume speaker role based on topic expertise
   4. NEVER merge similar-sounding speakers
   5. If speaker does not self-identify, label as SPEAKER_XX_UNKNOWN
   6. Return all identified speakers, even if uncertain
   
   Return JSON:
   {
     "speakers": [
       {"speaker_id": "SPEAKER_00", "name": "Name or null", "role": "host|co_host|guest|unknown"},
       ...
     ],
     "identification_method": "self-introduction|direct_address|metadata_match|unknown",
     "confidence": 0.0 to 1.0,
     "evidence": "Quote or reasoning"
   }
   ```

3. **Example prompt:**
   ```
   Use the transcript excerpt below to identify speakers. Apply CRITICAL RULES above.
   
   Title: "Regenerative Finance with Gregory Landua & Monty Bryant"
   
   Transcript (first ~8000 tokens):
   [SPEAKER_00 00:00] "Hi, I'm Gregory Landua, host of the Regen podcast. Today we're talking with..."
   [SPEAKER_01 00:15] "Great to be here. I'm Monty Bryant from Regen Network."
   [SPEAKER_00 00:30] "Monty, can you tell us about..."
   
   Return: {"speakers": [...], "identification_method": "...", "confidence": ..., "evidence": "..."}
   ```

4. **Output:** `transcript_speakers: {speakers: [{speaker_id, name, role, confidence}], method, evidence}`

---

## Stage 3: User Override

**Goal:** Allow user to provide explicit speaker names if automated guesses are wrong.

**Process:**

1. **Accept --speakers flag** — Comma-separated list of speaker names, in order they appear:
   ```bash
   --speakers "Gregory Landua,Monty Bryant"
   ```

2. **Accept natural language** — If user says "Gregory is the host, Monty is the first guest", parse natural language to extract roles.

3. **Map to diarized speakers** — Take user input and map SPEAKER_00, SPEAKER_01, etc. to names and roles.

4. **Validation** — Confirm number of named speakers matches number of diarized speakers (or warn if mismatch).

---

## Mapping: Speaker Label Assignment

Once speakers are identified, map diarized labels to canonical names and roles.

**Map function: `map_speakers_by_order`**

```python
def map_speakers_by_order(diarized_speakers, identified_speakers):
  """
  diarized_speakers: list of speaker labels from diarization [SPEAKER_00, SPEAKER_01, ...]
  identified_speakers: list of names/roles from identification [
    {name: "Gregory", role: "host"},
    {name: "Monty", role: "guest"},
    ...
  ]
  
  Returns: mapping dict {SPEAKER_00: "Gregory Landua", SPEAKER_01: "Monty Bryant", ...}
  """
  
  # Assume diarized speakers appear in same order as identified speakers
  mapping = {}
  for i, speaker_label in enumerate(diarized_speakers):
    if i < len(identified_speakers):
      mapping[speaker_label] = identified_speakers[i]["name"]
    else:
      mapping[speaker_label] = f"{speaker_label}_UNKNOWN"
  
  return mapping
```

**Unresolved speakers:** If diarization finds more speakers than identification, assign remaining as `SPEAKER_XX_UNKNOWN`. Log warning: "Diarization found {N} speakers; only {M} identified. Remaining speakers labeled SPEAKER_XX_UNKNOWN."

---

## Frontmatter Shape

Frontmatter must include speaker information in one of two shapes:

### Shape A: Host + Co-host + Guest(s)

```yaml
---
title: "Episode Title"
source: youtube
channel: "Podcast Name"
published: 2025-04-10
duration: 45
transcript_method: whisperx_local
pathway: P2
quality: high
host: Gregory Landua
co_host: Monty Bryant
guest:
  - Alice Smith
  - Bob Johnson
---
```

Use this shape if roles are clear (one host, optional co-host, multiple guests).

### Shape B: Speakers List

```yaml
---
title: "Episode Title"
source: youtube
channel: "Podcast Name"
published: 2025-04-10
duration: 45
transcript_method: whisperx_local
pathway: P2
quality: high
speakers:
  - name: Gregory Landua
    role: host
  - name: Monty Bryant
    role: co_host
  - name: Alice Smith
    role: guest
---
```

Use this shape if roles are ambiguous or non-standard (e.g., panel discussion, co-hosts ≥3).

**Empty case:** If no speakers identified, omit host/co_host/guest/speakers entirely. Do not use `host: null`.

---

## Anti-Patterns: What NOT to Do

### NEVER Fabricate Speaker Names from Topic Context

**Bad:**
```
Transcript mentions "carbon credits" frequently.
Assume speakers are "ReFi expert" or "Carbon specialist".
```

**Correct:**
```
Transcript mentions "carbon credits" but speakers don't self-identify.
Label as SPEAKER_00_UNKNOWN, SPEAKER_01_UNKNOWN.
Ask user or flag for manual review.
```

---

### NEVER Assume First Speaker = Host

**Bad:**
```
Transcript starts with SPEAKER_00 speaking.
Assume SPEAKER_00 is the host; remaining are guests.
```

**Correct:**
```
Transcript opens with SPEAKER_00. But they might be:
  - Guest introducing themselves
  - Background speaker or sound effect
  - Moderator (not host)
  - Interviewer (possibly host, but verify with evidence)
Wait for explicit identification ("I'm the host") or metadata match.
```

---

### NEVER Merge Two Diarized Speakers Because They "Sound Similar"

**Bad:**
```
Diarization produces SPEAKER_00 and SPEAKER_01.
Listener thinks they sound similar, assumes same person.
Manually merge labels.
```

**Correct:**
```
Trust diarization model. If model says two speakers, respect that.
If merge is truly needed, flag as [POTENTIAL_SPEAKER_MERGE] in output for user review.
Do not silently merge.
```

---

### NEVER Override Diarization Without Explicit User Confirmation

**Bad:**
```
Diarization finds 3 speakers; metadata lists 2.
Assume diarization is wrong; use metadata only.
Silently ignore diarization output.
```

**Correct:**
```
Log mismatch: "Diarization found 3 speakers; metadata lists 2. Possible scenarios:
  A) Background speaker detected as separate (e.g., opening music)
  B) One speaker's voice variation caused split
  C) Metadata incomplete
  
Use diarization as primary; ask user if mismatch concerns them."
```

---

## Implementation Checklist

- [ ] Metadata research: Extract from title/description using GPT-4o-mini
- [ ] Transcript guess: Feed first ~8000 tokens, apply CRITICAL RULES
- [ ] User override: Accept --speakers flag and natural language input
- [ ] Mapping: Assign diarized labels to identified speakers
- [ ] Frontmatter: Choose Shape A or B based on clarity of roles
- [ ] Anti-patterns: Verify no fabrication, assumption, merging, or overriding without user consent
- [ ] Logging: Record all speaker identification decisions, confidence scores, and evidence
- [ ] Edge cases: Handle unresolved speakers, metadata/diarization mismatches gracefully
