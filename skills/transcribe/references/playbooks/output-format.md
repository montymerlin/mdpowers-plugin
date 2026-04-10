# Output Format Specification

Complete contract for transcript file structure, YAML frontmatter, markdown body layout, and filename conventions.

## YAML Frontmatter Contract

All transcripts output a YAML frontmatter block followed by markdown body. Frontmatter must be valid YAML (tools: yamllint).

### Required Fields (All Pathways)

These fields **must** be present and populated:

```yaml
title: "Exact Title from Source (or User-Provided)"
source: "youtube | local | api_assemblyai | api_deepgram | api_rev | api_openai"
channel: "Channel/Podcast/Creator Name or ID"
published: "YYYY-MM-DD format (extracted from metadata)"
duration: 45  # Integer, minutes
transcript_method: "manual_subs | auto_captions | whisper_api | whisperx_local | <service_name>"
pathway: "P1 | P2 | P3"
quality: "high | medium | degraded"
quality_notes: "Brief explanation if quality < high (e.g., 'auto-captions only', 'OOM, reverted to segment-level')"
vocab_master_version: "YYYYMMDD or 'none' if no master used"
vocab_overlay: "filename or path, or 'none'"
transcribed_at: "ISO 8601 timestamp with timezone (e.g., 2025-04-10T14:32:15-07:00)"
```

### Conditional Fields

Include these **if applicable**:

#### For identified speakers (Path 2 typically):

Choose **one** of Shape A or Shape B below.

**Shape A: Host + Co-host + Guest(s)**
```yaml
host: "Gregory Landua"
co_host: "Monty Bryant"  # Optional
guest:
  - "Alice Smith"
  - "Bob Johnson"
```

Use Shape A when roles are clear and unambiguous.

**Shape B: Speakers List**
```yaml
speakers:
  - name: "Gregory Landua"
    role: "host"
  - name: "Monty Bryant"
    role: "co_host"
  - name: "Alice Smith"
    role: "guest"
```

Use Shape B when roles are ambiguous or non-standard (panel discussions, ≥3 co-hosts).

#### For API service transcriptions (P3):

```yaml
api_cost: "$0.12"
api_service: "assemblyai"
api_job_id: "abc123..."  # For tracking/audit
```

#### For vocabulary corrections (optional but recommended):

```yaml
vocab_corrections_applied: 5
vocab_corrections: 
  - {original: "defI", corrected: "DeFi", source: "vocab_overlay"}
  - {original: "nft assets", corrected: "NFT assets", source: "vocab_overlay"}
```

#### For checkpoint-based transcriptions (P2):

```yaml
cache_location: ".mdpowers/cache/VIDEO_ID"
checkpoint_files: ["01_transcription.json", "02_alignment.json", "03_diarization.json", "04_merged.json", "05_speaker_map.json"]
```

### Optional Metadata

```yaml
language: "en"  # ISO 639-1 code
confidence_score: 0.87  # Average confidence across transcript
diarization_speakers: 3  # Number of unique speakers detected
tags:
  - "podcast"
  - "regen"
  - "finance"
```

---

## Markdown Body Shapes

### Path 1: No Speakers, Flat Timeline

For P1 (YouTube fast) or transcriptions without diarization:

```markdown
---
[YAML frontmatter as above]
---

[00:00] Opening remarks introducing the topic.

[00:30] First speaker begins with their thoughts on regenerative finance and carbon markets.

[01:15] Transition to discussion of blockchain-based mechanisms for verification and trust.

[02:45] Q&A section begins. Host asks about scalability concerns in current implementations.

[05:30] Key takeaway: The intersection of ReFi and traditional nature finance requires institutional...

[06:00] End of segment.
```

**Rules:**
- One timestamp per logical utterance or sentence block (not every word)
- Format: `[HH:MM.ss]` at line start, followed by text
- Timestamps must be monotonically increasing
- No speaker labels; all text treated as single continuous stream
- Preserve paragraph breaks for readability

### Path 2: Bold Speaker Blocks with Timestamps

For P2 (WhisperX) or transcriptions with diarization:

```markdown
---
[YAML frontmatter as above]
---

**Gregory Landua** [00:00] Welcome to the Regen podcast. Today we're exploring the intersection of regenerative finance and nature-based solutions. Joining us is Monty Bryant from Regen Network.

**Monty Bryant** [00:18] Thanks for having me, Gregory. It's great to be here.

**Gregory Landua** [00:25] Can you tell us what Regen Network does?

**Monty Bryant** [00:35] Absolutely. Regen Network is a blockchain-based ecosystem for ecological regeneration. We focus on carbon credits, biodiversity credits, and verified nature projects that...

**Gregory Landua** [02:10] That's fascinating. How does tokenization change the game for carbon markets?

**Monty Bryant** [02:25] Well, tokenization allows for fractional ownership, instant settlement, and programmable incentives. Traditional carbon markets require intermediaries and have high friction costs...
```

**Rules:**
- Bold speaker name at start of new speaker turn: `**Name** [timestamp]`
- One timestamp per speaker turn (multiple sentences okay in single turn)
- Preserve natural conversation flow (speaker overlap marked as [OVERLAP] if detected)
- Blank line between speaker turns for readability
- All text under a speaker label belongs to that speaker until next bold label

#### Handling Overlapping Speech (Path 2 Only)

If two speakers overlap (both speaking simultaneously):

**Option A: Merge into one speaker's turn**
```markdown
**Gregory Landua** [00:45] So what's your take on—

**Monty Bryant** [00:47] —the regulatory landscape? [OVERLAP: both spoke] I think we need clarity first.
```

**Option B: Separate with overlap marker**
```markdown
**Gregory Landua** [00:45] So what's your take on the regulatory landscape?

[OVERLAP: Monty Bryant and Gregory Landua spoke simultaneously 00:47-00:50]

**Monty Bryant** [00:50] I think we need clarity first on the fundamentals.
```

Use Option A for minor overlaps; Option B for extended simultaneous speech.

---

## Output Path Convention

### Default Output Path

If user does not specify `--output`, use:

```
{cwd}/transcripts/{YYYY-MM-DD}_{SafeTitle}_{source_id}.md
```

**Components:**
- `{cwd}` — Current working directory (usually project root)
- `{YYYY-MM-DD}` — Today's date in ISO format
- `{SafeTitle}` — Title with unsafe characters stripped, max 80 characters
  - Remove: `/`, `\`, `:`, `?`, `"`, `<`, `>`, `|`, `*`
  - Replace: spaces → underscores or dashes (consistent)
  - Example: `"AI Ethics: The Future of Governance"` → `AI_Ethics_The_Future_of_Governance` or `AI-Ethics-The-Future-of-Governance`
- `{source_id}` — Video ID (YouTube: 11-char alphanumeric), filename (local), job ID (API), etc.

**Example paths:**
- `transcripts/2025-04-10_Regenerative_Finance_dQw4w9WgXcQ.md` (YouTube)
- `transcripts/2025-04-10_Podcast_Episode_202_abc123.md` (API service)
- `transcripts/2025-04-10_Interview_Recording_2025-04-10-interview.md` (local file)

### User-Specified Output Path

If user provides `--output /my/custom/path/episode.md`, use that path **verbatim**. Do not apply auto-naming conventions.

---

## Conflict Resolution: Overwrite Policy

### Scenario: File Already Exists at Output Path

**Never silently overwrite.** Instead:

1. **Check if output file exists** — Warn user: `"Output file already exists: {path}"`

2. **Offer options:**
   - **[O]verwrite** — Replace existing file (confirm explicitly)
   - **[V]ersion** — Save as `{path}_v2.md`, `{path}_v3.md`, etc. (auto-increment)
   - **[C]ancel** — Do not write; exit without error
   - **[N]ew path** — Prompt user for new path

3. **Default:** Version (safe default; no data loss). Only overwrite if user explicitly chooses [O].

**Example interaction:**
```
Output file exists: transcripts/2025-04-10_Episode_100_dQw4w9WgXcQ.md

Options:
  [O]verwrite
  [V]ersion (save as _v2, _v3, etc.)
  [C]ancel
  [N]ew path

Choose: [default=V]
```

---

## Validation Checklist

Before writing output file, validate:

- [ ] YAML frontmatter is syntactically valid (yamllint or equivalent)
- [ ] All required fields present and non-empty
- [ ] Title field is non-empty string
- [ ] Pathway is one of: P1, P2, P3
- [ ] Quality is one of: high, medium, degraded
- [ ] published field is valid ISO date (YYYY-MM-DD)
- [ ] duration is positive integer
- [ ] transcribed_at is valid ISO 8601 with timezone
- [ ] Markdown body contains at least one timestamp
- [ ] All timestamps in [HH:MM.ss] format
- [ ] Timestamps are monotonically increasing (no backwards jumps)
- [ ] For Path 1: no bold speaker labels in body
- [ ] For Path 2: all speaker turns start with **Name** [timestamp]
- [ ] No duplicate consecutive lines (same text back-to-back)
- [ ] File encodes as UTF-8 without BOM
- [ ] Total file size < 50MB (reasonable for audio content)

If any validation fails, report specific error and do not write file.

---

## Examples

### Example 1: P1 Output (YouTube Fast)

```yaml
---
title: "ReFi and Nature Finance: A Conversation with Gregory Landua"
source: youtube
channel: "Bridging Worlds Podcast"
published: 2025-04-08
duration: 47
transcript_method: manual_subs
pathway: P1
quality: high
quality_notes: "Manual YouTube captions used"
vocab_master_version: none
vocab_overlay: none
transcribed_at: 2025-04-10T14:32:15-07:00
language: en
tags:
  - regenerative-finance
  - nature-based-solutions
---

[00:00] Welcome to the Bridging Worlds podcast, where we explore the intersection of regenerative finance and mainstream development. I'm your host, and today we're discussing how blockchain technology and carbon markets are reshaping nature-based finance.

[00:35] Our guest is Gregory Landua, co-founder and Executive Director of Regen Foundation. Gregory has been instrumental in building bridges between the Web3 and environmental sectors.

[01:15] Gregory, thanks for being here.

[01:20] Thanks for having me. It's great to discuss these topics because there's so much confusion about ReFi and what it actually means in practice.

[02:00] Let's start with the basics. What is regenerative finance?
```

### Example 2: P2 Output (WhisperX Local)

```yaml
---
title: "ReFi and Nature Finance: A Conversation with Gregory Landua"
source: local
channel: "Bridging Worlds Podcast"
published: 2025-04-08
duration: 47
transcript_method: whisperx_local
pathway: P2
quality: high
quality_notes: ""
vocab_master_version: 20250410
vocab_overlay: vocabularies/regen-core.json
transcribed_at: 2025-04-10T14:32:15-07:00
language: en
host: "Podcast Host"
guests:
  - "Gregory Landua"
diarization_speakers: 2
cache_location: .mdpowers/cache/interview_2025-04-08
vocab_corrections_applied: 3
tags:
  - regenerative-finance
  - nature-based-solutions
---

**Podcast Host** [00:00] Welcome to the Bridging Worlds podcast, where we explore the intersection of regenerative finance and mainstream development. I'm your host, and today we're discussing how blockchain technology and carbon markets are reshaping nature-based finance.

**Podcast Host** [00:35] Our guest is Gregory Landua, co-founder and Executive Director of the Regen Foundation. Gregory has been instrumental in building bridges between the Web3 and environmental sectors. Gregory, thanks for being here.

**Gregory Landua** [00:55] Thanks for having me. It's great to discuss these topics because there's so much confusion about ReFi and what it actually means in practice. When I say regenerative finance, I mean the application of capital and incentive structures toward restoration of natural systems.

**Podcast Host** [01:45] That's a helpful definition. Can you walk us through how blockchain enables ReFi?

**Gregory Landua** [02:05] Sure. Traditional carbon markets have intermediaries taking 20-30% cuts, slow settlement, and limited transparency. Blockchain removes intermediaries and enables instant, programmatic incentives.
```
