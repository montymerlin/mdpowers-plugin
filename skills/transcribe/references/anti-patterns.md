# Anti-Patterns: Hard Rails

Explicit list of what must NEVER happen, with explanations and consequences. These are guardrails that must be enforced at runtime.

---

## 1. NEVER Fabricate Speaker Names from Topic Context

**Anti-pattern:**
```
Transcript discusses carbon markets, ReFi, blockchain.
Skill assumes speakers are "carbon expert" or "crypto specialist".
Labels speakers based on what they talk about, not who they are.
```

**Why this fails:**
- A guest might discuss carbon markets without being a carbon expert
- Guest credentials are unknown from topic alone
- Fabricated names are misleading and reduce transcript credibility

**Correct behavior:**
```
Transcript has diarized speakers SPEAKER_00, SPEAKER_01.
No self-introductions found in first 8000 tokens.
Label as SPEAKER_00_UNKNOWN, SPEAKER_01_UNKNOWN.
Ask user: "Who are these speakers?" or prompt for metadata research.
```

**Enforcement:**
- Speaker ID LLM prompt includes CRITICAL RULE: "NEVER assume role based on topic expertise"
- Block any speaker name that appears zero times in transcript text
- Require explicit evidence: self-introduction, direct address, or user override

---

## 2. NEVER Assume First Speaker = Host

**Anti-pattern:**
```
Transcript starts with SPEAKER_00 speaking.
Skill assumes: "First speaker must be host; rest are guests."
Assign host role without evidence.
```

**Why this fails:**
- First speaker might be a guest introducing themselves
- Opening might be a pre-recorded intro (not a speaker)
- Moderator speaking first doesn't make them the host

**Correct behavior:**
```
First speaker in transcript is unknown unless:
  - They explicitly say "I'm the host" or "I host this show"
  - Metadata (title/description) explicitly names them as host
  - User confirms via --speakers flag

Otherwise: Label as SPEAKER_00_UNKNOWN and flag for user review.
```

**Enforcement:**
- Speaker ID LLM: Require CRITICAL RULE "NEVER assume first=host"
- Diarization mapper: Do NOT auto-assign host role based on speaker order
- Output validation: If host is inferred without evidence, emit warning

---

## 3. NEVER Merge Two Diarized Speakers Because They "Sound Similar"

**Anti-pattern:**
```
Diarization output: SPEAKER_00, SPEAKER_01
Human listener thinks: "They sound alike; must be same person."
Skill silently merges SPEAKER_01 into SPEAKER_00.
```

**Why this fails:**
- Voice similarity ≠ same speaker (could be family members, similar accents)
- Diarization model is trained on this distinction
- Silent merge loses information without user awareness

**Correct behavior:**
```
Trust diarization model output.
If merge needed: Flag as [POTENTIAL_SPEAKER_MERGE] in output for user review.
Never silently merge two speakers.
```

**Enforcement:**
- No automatic speaker merging in code (except explicit --merge-speakers flag)
- If user suspects false positives: Offer review with audio samples and confidence scores
- Log all speaker merges with reasoning

---

## 4. NEVER Silently Degrade Quality on Explicit User Pathway Override

**Anti-pattern:**
```
User specifies: --pathway P2 (WhisperX local, full diarization)
Environmental issue occurs (OOM, CUDA error).
Skill silently downgrades to Whisper API (P1-like).
User unaware that output quality degraded.
```

**Why this fails:**
- User explicitly chose P2 for full control and reproducibility
- Silent downgrade breaks expectation of local processing
- Output is functionally different than promised

**Correct behavior:**
```
User chooses P2 explicitly.
If environment can't support P2: Stop, report error clearly.
Options: Retry, use smaller model, use CPU, or fall back to P1 WITH user confirmation.
Never silently degrade without notification.
```

**Enforcement:**
- Validate pathway choice against environment at start
- If resource insufficient for chosen pathway: Raise error immediately
- Offer alternatives: "Not enough GPU for large model. Retry with base model? [Y/n]"
- Only proceed with degradation if user explicitly agrees

---

## 5. NEVER Skip the Review Phase

**Anti-pattern:**
```
Pathway 2 completes diarization.
Skill automatically writes output without review.
User never sees intermediate outputs (timestamps, speaker assignments, corrections).
```

**Why this fails:**
- Hallucinations, misalignments, speaker confusion go unnoticed
- User can't correct errors before output is final
- Quality degradation is invisible

**Correct behavior:**
```
After each major pipeline stage (transcription, diarization, vocabulary correction):
  1. Generate summary/report of what happened
  2. Ask user: "Review outputs? [Y/n] (default=Y)"
  3. If yes: Show highlights, allow edits before write
  4. If no (power users): Proceed to write
```

**Enforcement:**
- Interactive review prompt after diarization (if in interactive mode)
- Batch mode: Save draft to `.mdpowers/cache/review_before_output.txt`
- Never auto-write final output without user confirmation (or explicit --force flag)

---

## 6. NEVER Commit .mdpowers/cache/ Files to Git

**Anti-pattern:**
```
.mdpowers/cache/ contains 1–2GB of checkpoint JSONs, audio files, models.
Skill runs without .gitignore rule.
User accidentally commits cache to git.
Repo bloats; CI/CD fails.
```

**Why this fails:**
- Cache is machine-generated and reproducible; no need for version control
- Models are external and don't belong in code repos
- Inflates repository size

**Correct behavior:**
```
Add to .gitignore: /.mdpowers/cache/
User can keep cache locally for speed.
Cache is never tracked by git.
```

**Enforcement:**
- Setup wizard auto-adds to .gitignore (Step 5)
- Pre-commit hook warns if cache files staged: "Don't commit .mdpowers/cache/; run 'git rm --cached .mdpowers/cache/'"
- Output warning if user manually stages cache files

---

## 7. NEVER Run WhisperX ctranslate2 on MPS — Force CPU Even on Apple Silicon

**Anti-pattern:**
```
macOS with Apple Silicon (M1/M2).
torch.backends.mps.is_available() = true
Skill runs whisperx with device=mps
ctranslate2 crashes: "Unsupported device: MPS"
```

**Why this fails:**
- ctranslate2 (Whisper's underlying runner) does NOT support MPS
- MPS auto-detection appears to work but causes runtime error
- Error occurs late in pipeline, wasting time

**Correct behavior:**
```
Environment detection:
  If mps_available and using whisperx:
    Force CUDA_VISIBLE_DEVICES="" and TORCH_DEVICE=cpu for transcription/alignment
  Allow pyannote to use MPS (it supports it fine)

Log clearly: "Using CPU for WhisperX (ctranslate2 incompatible with MPS).
Diarization will use MPS for speed."
```

**Enforcement:**
- Environment check (setup.py or first run) detects Apple Silicon
- Explicitly set device constraints before invoking whisperx
- Runtime validation: If ctranslate2 error detected, wrap with clear message pointing to this rule
- Documentation: Highlight in `environments.md` with CRITICAL flag

---

## 8. NEVER Auto-Union Mistranscription Lists on Promotion — Show Diff, Let User Decide

**Anti-pattern:**
```
Master vocabulary: {"aum": "Assets Under Management", "regen": "Regen Network"}
Overlay (from vocab review): {"aum": "AUM", "regen": "Regen"}
Skill merges: {"aum": ["Assets Under Management", "AUM"], "regen": [...]}
User never sees the conflict; both forms now "correct".
```

**Why this fails:**
- Conflicting canonical forms are ambiguous
- User may have intentionally corrected the term
- Union obfuscates the decision that was made

**Correct behavior:**
```
On promotion conflict:
  Master has: "aum" → "Assets Under Management"
  Overlay has: "aum" → "AUM"
  
  Show diff to user:
    Master: Assets Under Management
    Overlay: AUM
    
  Ask: "Which is canonical? Keep master? Use overlay? Merge as both?"
  
  Update chosen version; do not silently union.
```

**Enforcement:**
- Promotion workflow compares old vs. new values
- If conflict detected: Block auto-merge; require user decision
- Store decision in vocab_corrections log for audit

---

## 9. NEVER Hardcode Output Paths — Always Resolve from User Input or Convention

**Anti-pattern:**
```
Skill hardcodes: output_path = "/tmp/transcripts/"
User's custom --output flag is ignored
Transcript ends up in /tmp, user can't find it
```

**Why this fails:**
- Ignores explicit user choice
- Output may disappear on reboot (if /tmp is cleared)
- Breaks reproducibility and user control

**Correct behavior:**
```
Output path resolution (in order of priority):
  1. User-provided --output flag (if given)
  2. Environment variable MDPOWERS_OUTPUT (if set)
  3. Config: output_path from .mdpowers/config.json
  4. Convention: {cwd}/transcripts/{YYYY-MM-DD}_{SafeTitle}_{source_id}.md
  
Never skip a priority level.
```

**Enforcement:**
- Validate --output before using; confirm with user if path differs from default
- Log chosen path in output frontmatter: `output_path_used: "..."`
- Runtime check: If user-provided path is unusual (e.g., non-existent parent dir), confirm

---

## 10. NEVER Run Path 2 Inside a Sandboxed Host — Emit a Script Instead

**Anti-pattern:**
```
User in a sandboxed host requests P2 transcription.
Skill attempts to run whisperx inside sandbox.
Models don't exist, GPU access fails, process hangs.
User frustrated; transcription never completes.
```

**Why this fails:**
- Sandboxes have limited compute resources and no GPU
- Model downloads would exceed memory/bandwidth limits
- Full local pipeline (30+ min on GPU) infeasible in interactive session

**Correct behavior:**
```
If in a sandboxed host and user requests P2:
  Display:
    "P2 (WhisperX local) requires significant compute and isn't available in this sandboxed host.
     
     Options:
     [1] Use P1 (YouTube fast) instead
     [2] I'll generate a script you can run locally
     [3] Choose P3 (API service) — faster, cloud-based
     
     Choose [default=1]:"
  
  If [2]: Generate executable shell script (.sh file)
    - Script downloads audio
    - Runs whisperx locally with model selection
    - Uploads result back (if applicable)
    - User runs: bash ./transcribe_local.sh
```

**Enforcement:**
- Sandbox detection at pathway selection
- P2 check: `if in_sandbox and pathway == "P2": raise SandboxNotSupported("...generate script message...")`
- Script generation includes all necessary error handling and progress reporting

---

## 11. NEVER Overwrite an Existing Transcript Without Confirmation

**Anti-pattern:**
```
User runs transcription again; output path already exists.
Skill silently overwrites previous transcript.
User loses their edits or previous version without warning.
```

**Why this fails:**
- Previous output may have user edits or annotations
- No warning or backup created
- Data loss without user consent

**Correct behavior:**
```
If output file exists:
  Display: "Output file already exists: {path}"
  
  Ask user: "What should I do?"
    [O]verwrite (confirm explicitly)
    [V]ersion (save as _v2.md, _v3.md, ...)
    [C]ancel (exit without writing)
    [N]ew path (prompt for alternative path)
  
  Default: [V]ersion (safe default; no data loss)
  
  Only proceed with [O] after explicit user confirmation.
```

**Enforcement:**
- File existence check before write
- Overwrite requires user choice [O] AND secondary confirmation
- Version numbering: auto-increment _v2, _v3, etc.

---

## 12. NEVER Include Hallucinated Timestamps in Path 1 Sub-Fetched Transcripts

**Anti-pattern:**
```
Path 1 (YouTube fast) retrieves auto-captions.
Some timestamps are missing or malformed.
Skill guesses missing timestamps: [00:15] → [00:20] based on text length.
Hallucinated timestamps are silently included in output.
```

**Why this fails:**
- Guessed timestamps have no basis in source material
- User might rely on timestamps for editing or reference
- Reduces transcript credibility

**Correct behavior:**
```
Path 1 timestamp handling:
  - Use subtitle cue timestamps as-is
  - If cue is missing timestamp: Mark as [TIMESTAMP_MISSING]
  - Never interpolate or guess missing timestamps
  - Log count of missing timestamps in quality_notes
  
  Example:
    [00:15] "First part of sentence"
    [TIMESTAMP_MISSING] "continued thought from cue with no time marker"
    [00:25] "Next clear cue"
```

**Enforcement:**
- Subtitle parser: Extract only timestamps present in VTT
- Quality check: If >10% of cues missing timestamps, quality degrades to medium
- Output validation: No timestamps should appear that weren't in source

---

## Summary Enforcement Checklist

Before any transcription completes, verify:

- [ ] No fabricated speaker names (check against transcript text)
- [ ] First speaker not auto-labeled as host (verify evidence)
- [ ] No silent speaker merges (log all changes)
- [ ] Pathway degradation explicitly confirmed by user
- [ ] Review phase completed (or explicitly skipped with --force)
- [ ] .mdpowers/cache/ not staged in git
- [ ] Apple Silicon + WhisperX = CPU forced
- [ ] Vocabulary conflicts shown to user (not silently merged)
- [ ] Output path from user input or convention (not hardcoded)
- [ ] P2 in sandbox = script generated instead of attempted
- [ ] Overwrite confirmation received (version fallback default)
- [ ] Path 1 timestamps from source only (no hallucinations)

All twelve anti-patterns are critical runtime guards. Violations should raise errors or emit clear warnings.
