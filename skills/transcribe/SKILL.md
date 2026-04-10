---
name: transcribe
description: Transcribe audio and video to structured, speaker-labelled markdown with adaptive vocabulary correction. Use when the user asks to "transcribe", "get a transcript", "transcribe this video", "transcribe this podcast", "transcribe this audio", provides a YouTube URL they want transcribed, mentions "diarization", "speaker labels", or asks to process audio/video into text. Handles YouTube videos (native subtitles or Whisper API fallback), local audio files (WhisperX + pyannote diarization), and stubs for cloud API services. Vocabulary priming and post-correction use a cascading global + project-local overlay system.
---

# transcribe

> **Guides not rails.** Everything below is a default, not a mandate. Pathway descriptions, playbooks, and phase instructions exist so you don't have to re-derive good choices every time — not to override your judgment when the situation calls for something different. If a source would be better served by a different approach, take it, name what you changed, and proceed. The worst failure mode isn't deviating from the playbook — it's following it blindly and producing something worse than judgment would have. Hard rails are listed in `references/anti-patterns.md`. Everything else is soft.

## What this skill does

Transcribes audio and video sources into structured markdown with YAML frontmatter, timestamped text, optional speaker diarization, vocabulary-aware correction, and LLM-generated summaries. The output isn't raw text — it's an AI-readable, human-reviewable document that other agents and people can navigate, search, cite, and reason over.

## When to use

- User provides a YouTube URL and wants a transcript
- User has a local audio/video file (mp3, m4a, wav, ogg, flac, mp4, webm) to transcribe
- User asks for speaker identification, diarization, or "who said what"
- User wants vocabulary-corrected transcripts (domain-specific terms, proper nouns)
- User wants to transcribe a batch (playlist, folder of files, season of episodes)

## The four phases

Every transcription moves through four phases. Like the convert skill's five phases, these are conceptual — they compress or expand depending on complexity.

1. **Probe** — detect the source type, check the environment, load vocabulary
2. **Route** — choose the best pathway based on probe results, user intent, and environment
3. **Run** — execute the chosen pathway's pipeline
4. **Review** — present results, flag quality issues, offer vocabulary candidate promotion

## Phase 1 — Probe

Run `scripts/probe.py` (or invoke its logic directly). Probe does three things in parallel:

**(a) Source detection.** Parse the input — is it a YouTube URL, a local file path, or a folder of files? For YouTube: fetch video metadata (title, channel, duration, available subtitle tracks). For local files: check format, size, duration via ffprobe.

**(b) Environment detection.** Check what's installed: yt-dlp, ffmpeg/ffprobe, whisperx, pyannote, torch (and device: CUDA, MPS, CPU), OpenAI API key. Detect host mode (local vs sandbox) using `lib/host_mode.py`.

**(c) Vocabulary detection.** Walk the discovery cascade (see `references/playbooks/vocabulary-handling.md`): `$MDPOWERS_VOCAB` → XDG master → workspace `.mdpowers/vocabulary.*.json` overlays → merge. Report what was found and loaded.

Output: a short profile carried into Route. Example:
```
Source: YouTube video "ReFi Podcast Ep. 42" (47:23, manual subs available)
Environment: local mode, yt-dlp ✓, whisperx ✓ (CPU), pyannote ✓ (MPS), OPENAI_API_KEY ✓
Vocabulary: master (142 terms) + overlay bridging-worlds (23 terms) = 165 active terms
```

## Phase 2 — Route

Choose a pathway based on the probe results. Three pathways exist:

### Intent routing table

| Signal | Pathway | Why |
|--------|---------|-----|
| YouTube URL + subs available | **P1** | Fast, no compute needed |
| YouTube URL + no subs + no whisperx | **P1** (Whisper API fallback) | API handles it |
| YouTube URL + user wants diarization | **P2** | Needs local pipeline |
| Local audio file + whisperx installed | **P2** | Full local pipeline |
| Local audio file + no whisperx | **P1** (Whisper API) | Graceful degradation |
| User explicitly requests an API service | **P3** | Stub — not yet implemented |
| Sandbox mode + P2 requested | **Script emission** | Can't run locally in sandbox |

**Routing rules:**

- If the user explicitly requests a pathway, honour it. If the environment can't support it, **stop and explain** — never silently degrade on explicit override (anti-pattern #4).
- If routing to P1 via Whisper API fallback (no native subs, no whisperx), mark `quality: degraded` in frontmatter and explain the degradation to the user.
- If in sandbox mode and P2 is the best choice, use `scripts/emit_run_script.py` to generate a local run script instead of attempting execution.

### Batch handling

If the user provides multiple URLs, a playlist, or a folder:
- **Pause and confirm** before starting: show count, estimated time, output location.
- Process sequentially unless user explicitly says "batch run" or "do the whole playlist."
- Report progress between items.

## Phase 3 — Run

Execute the chosen pathway. Each pathway has a detailed reference file:

- **P1 — YouTube Fast:** `references/pathways/P1-youtube-fast.md`, runner: `scripts/yt_fast.py`
- **P2 — WhisperX Local:** `references/pathways/P2-whisperx-local.md`, runner: `scripts/whisperx_local.py`
- **P3 — API Service:** `references/pathways/P3-api-service.md`, runner: `scripts/api_service.py` (stub)

### What each pathway produces

**P1 (YouTube Fast):**
- Fetches native subtitles (manual → auto-generated) or falls back to Whisper API
- Flat timestamped markdown (no speaker blocks)
- Vocabulary post-correction applied
- LLM summary generated
- Fast: typically 30–120 seconds

**P2 (WhisperX Local):**
- Downloads audio, runs WhisperX transcription (CPU — ctranslate2 does NOT support MPS)
- Runs pyannote diarization (can use MPS on Apple Silicon)
- Speaker assignment via overlap voting
- Speaker identification via metadata research + LLM guess
- Vocabulary priming (Whisper initial_prompt) + post-correction
- LLM quirks review (confidence-gated autocorrection)
- Vocabulary candidate discovery
- Bold speaker-labelled markdown blocks
- Checkpointed: resumable from `.mdpowers/cache/{video_id}/`
- Slower: 5–30 minutes depending on duration and hardware

**P3 (API Service — stub):**
- Not yet implemented (v0.2 target)
- Will support AssemblyAI, Deepgram, Rev.ai
- Currently raises `NotYetImplemented` with guidance

### Graceful degradation

When the environment can't support the ideal pathway:

| Situation | Behaviour |
|-----------|-----------|
| P2 requested but whisperx missing | Offer P1 fallback, mark `quality: degraded` |
| P2 OOM on large-v2 model | Retry with medium model, then fall back to Whisper API |
| No OPENAI_API_KEY | P2 still works (local only). P1 Whisper fallback unavailable — warn user |
| Sandbox mode + P2 | Emit run script via `scripts/emit_run_script.py` |
| yt-dlp auth wall | Stop, explain, suggest manual download + P2 |

**Critical:** never silently degrade when the user explicitly chose a pathway. Stop, explain, offer alternatives.

## Phase 4 — Review

After the run completes:

1. **Present the output** — show the file path, a brief quality summary, and the frontmatter metadata.

2. **Flag quality issues** — if quality degraded, timestamps are missing, speaker count seems wrong, or vocabulary corrections were heavy, say so explicitly.

3. **Vocabulary candidates** — if P2 ran and discovered new vocabulary candidates (terms that appear frequently but aren't in the master vocab), present them and offer to promote to the project overlay or master vocabulary. See `references/playbooks/vocabulary-handling.md` for the promotion workflow.

4. **Speaker review** — if speakers were identified via LLM guess (not user-provided), flag them as provisional and offer the user a chance to correct before finalising.

5. **Overwrite handling** — if the output path already existed, the skill should have offered versioning (_v2, _v3) rather than silent overwrite. Confirm the final path.

## Playbooks

These are the detailed reference guides for cross-cutting concerns:

- `references/playbooks/vocabulary-handling.md` — discovery cascade, priming, post-correction, candidate discovery, promotion workflow
- `references/playbooks/speaker-identification.md` — three-stage flow (metadata research → LLM guess → user confirmation), mapping, anti-patterns
- `references/playbooks/output-format.md` — YAML frontmatter contract, markdown body shapes, filename conventions, overwrite handling

Read the relevant playbook before executing the corresponding part of a pathway.

## Environment and setup

- `references/environments.md` — dependency matrix, platform notes, env vars, install tiers
- `references/setup.md` — local-mode setup walkthrough
- `references/setup-sandbox.md` — sandbox-mode setup via chat UI
- `references/anti-patterns.md` — 12 hard rails that must never be violated

First-time users should run `/transcribe setup` to initialise vocabulary files, check dependencies, and configure their environment. The setup command is documented in `commands/transcribe-setup.md`.

### Dependency tiers

**Tier 1 (core):** yt-dlp, openai, python-dotenv, tiktoken — required for P1.
**Tier 2 (heavy):** whisperx, pyannote-audio, torch, torchaudio — required for P2. Install via `scripts/install_path2.sh`.
**Tier 3 (NLTK):** NLTK words corpus — optional, improves vocabulary candidate filtering. Install via `scripts/install_nltk_data.sh`.

## Host mode awareness

This skill runs in two host modes:

- **Local** (Claude Code terminal, Cursor): full subprocess access, real filesystem, GPU available. All pathways execute directly.
- **Sandbox** (Cowork): sandboxed mount, no GPU, session timeouts. P1 works directly. P2 requires script emission — the skill generates a `.sh` file the user runs on their local machine.

Host mode is auto-detected by `lib/host_mode.py` (heuristics: `/sessions/` path, `$CLAUDECODE`, `$CURSOR_AGENT`) and can be explicitly overridden via `$MDPOWERS_HOST_MODE=local|sandbox`.

## Commons-awareness

If you detect a `CLAUDE.md` in the working tree, read it and honour any conventions it declares. Watch for filename conventions, output directory preferences, and commit policy. Name what you're applying at the start of your response.

## Relationship to other skills

- **`mdpowers:convert`** — sibling skill for documents (PDF, docx, pptx → markdown). If the user has a document, use convert. If they have audio/video, use transcribe.
- **`mdpowers:clip`** — sibling skill for web pages → markdown. If the source is a URL that isn't a video, use clip.
- **Deprecated:** `mdpowers:pdf-convert` — replaced by convert. Do not use.
- **Superpowers skills** (if installed) — `two-stage-review` for prose quality review after transcription, `brainstorming` for unusual transcription challenges. Optional siblings, not hard dependencies.

## References

- `references/pathways/P1-youtube-fast.md` — YouTube fast pathway (10 steps)
- `references/pathways/P2-whisperx-local.md` — WhisperX local pathway (18 steps, checkpointed)
- `references/pathways/P3-api-service.md` — API service stub (v0.2 plan)
- `references/playbooks/vocabulary-handling.md` — vocabulary discovery, priming, correction, promotion
- `references/playbooks/speaker-identification.md` — three-stage speaker flow
- `references/playbooks/output-format.md` — frontmatter contract, markdown shapes, filename conventions
- `references/environments.md` — dependency matrix, platform notes, install tiers
- `references/setup.md` — local setup walkthrough
- `references/setup-sandbox.md` — sandbox setup walkthrough
- `references/anti-patterns.md` — 12 hard rails
