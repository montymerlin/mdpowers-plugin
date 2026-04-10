---
title: Transcribe Skill — Design Spec
status: approved
version: v0.1
date: 2026-04-09
author: Monty Bryant + Claude
---

# Transcribe Skill — Design Spec (v0.1)

This document captures the approved design for the `transcribe` skill, a new addition to the mdpowers plugin. It was produced via a superpowers brainstorming session on 2026-04-09 and approved section-by-section. Once execution begins, this spec is the source of truth — changes during build should be logged in DECISIONS.md with references back to the section numbers here.

## Purpose

Port Monty's existing transcription system (from `montymerlinHQ/tools/`) into a host-agnostic skill that works across Claude Code, Cursor, and Cowork. Provide multiple pathways tuned to different quality/speed/cost tradeoffs, with YouTube as the primary v0.1 source.

## Foundational decisions

Locked before design began:

1. **Port strategy:** Lift + refactor. Break `diarize.py` (1527 lines) + `transcribe.py` (243 lines) + `yt_transcript.py` (234 lines) into focused, pathway-specific runners plus a shared `lib/` of reusable helpers.

2. **v0.1 scope:** Path 1 (YouTube fast) + Path 2 (WhisperX local) fully wired. Path 3 (API service) shipped as a documented stub that raises `NotImplementedError` with roadmap pointer.

3. **Vocabulary architecture:** Global master at `$XDG_DATA_HOME/mdpowers/vocabulary.json` + project-local overlays at `./.mdpowers/vocabulary.<scope>.json` + `/transcribe setup` flow + optional bundled template + promotion workflow (overlay → master).

4. **Pathway routing:** Adaptive probe with user override. Skill picks a pathway from probe data, but `--pathway fast|local|api` (or natural-language equivalent) is a hard override. Graceful degradation only when routing was adaptive, never when user was explicit.

5. **Skill shape:** Four-phase workflow (Probe → Route → Run → Review), pathway files in `references/pathways/`, playbooks for cross-pathway concerns in `references/playbooks/`, bundled Python in `scripts/` with helpers in `scripts/lib/`.

## Directory structure

```
mdpowers-plugin/
└── skills/
    └── transcribe/
        ├── SKILL.md                          # ~250 lines, orchestrator
        ├── references/
        │   ├── pathways/
        │   │   ├── P1-youtube-fast.md
        │   │   ├── P2-whisperx-local.md
        │   │   └── P3-api-service.md         # stub in v0.1
        │   ├── playbooks/
        │   │   ├── vocabulary-handling.md
        │   │   ├── speaker-identification.md
        │   │   └── output-format.md
        │   ├── environments.md               # probe + dependency matrix
        │   ├── setup.md                      # local setup wizard walkthrough
        │   ├── setup-sandbox.md              # sandbox setup playbook (sync with setup.md!)
        │   └── anti-patterns.md              # hard rails
        ├── scripts/
        │   ├── probe.py                      # shared source + env probe
        │   ├── yt_fast.py                    # Path 1 runner
        │   ├── whisperx_local.py             # Path 2 runner
        │   ├── api_service.py                # Path 3 stub
        │   ├── setup_wizard.py               # /transcribe setup (local mode)
        │   ├── emit_run_script.py            # sandbox-mode script emitter
        │   ├── install_path2.sh              # Path 2 heavy deps + model prefetch
        │   ├── install_nltk_data.sh          # NLTK words corpus
        │   ├── requirements.txt              # Tier 1 (core) deps
        │   └── lib/
        │       ├── __init__.py               # empty — explicit imports only
        │       ├── host_mode.py              # detect local vs sandbox, path mapping
        │       ├── vocabulary.py             # load, prime, correct, discover, promote
        │       ├── speakers.py               # metadata research, LLM guess, overlap assign
        │       ├── diarization_cleanup.py    # merge short blocks, validate counts
        │       ├── ytdlp_helpers.py          # cookie fallback, metadata, subs, audio
        │       ├── markdown_builder.py       # frontmatter + speaker blocks
        │       ├── llm_review.py             # summary, quirks review
        │       └── errors.py                 # TranscribeError hierarchy
        ├── assets/
        │   └── vocabulary.template.json      # empty schema template
        └── commands/
            └── transcribe-setup.md           # only slash command: /transcribe setup
```

## Phase 1 — Probe

**Purpose:** understand the source and the environment before committing to a pathway.

**Steps:**

1. Parse the user's request to extract source(s). v0.1 sources: YouTube URL or YouTube playlist URL. Local audio/video files are v0.2.
2. For each YouTube source: run `scripts/probe.py` which calls `yt-dlp --dump-json` to extract title, channel, duration, description, manual subs availability, auto-captions availability, auth wall status.
3. Probe the environment: `yt-dlp`, `ffmpeg`, Python imports (`whisperx`, `pyannote.audio`, `torch`), env vars (`OPENAI_API_KEY`, `HF_TOKEN`).
4. Probe the vocabulary state: `.mdpowers/` overlay in cwd or any ancestor, `$XDG_DATA_HOME/mdpowers/vocabulary.json` master, count terms in each.
5. Detect host mode: `local` (Claude Code / Cursor) vs `sandbox` (Cowork).
6. Emit a structured `ProbeReport` for Route to consume.

**Failure handling:** probe failures (404 on YouTube, missing ffmpeg, malformed URL) stop the pipeline with an actionable error. No silent fallbacks at probe stage.

## Phase 2 — Route

**Purpose:** pick the pathway, honoring user override if provided.

**Logic:**

1. If user supplied `--pathway fast|local|api` or said "use the X pathway", honor it. If not available, stop with install guidance. Never silently degrade on explicit override.
2. Otherwise apply adaptive rules:
   - **Path 1** if: YouTube source with manual or auto subs AND implied quality need is "rough transcript" (phrasing like "gist", "quick", "rough cut") OR content is known single-speaker (lecture, solo podcast, keynote).
   - **Path 2** if: multi-speaker content (panels, interviews, podcasts with guests) AND whisperx/pyannote available AND user OK with long run. Also if YouTube has no subs at all.
   - **Path 3** (v0.2+): multi-speaker + need it fast + willing to pay.
3. If adaptive routing picked Path 2 but environment can't support it, offer Path 1 as fallback with explicit confirmation. Set `quality: degraded` on the resulting output.
4. Announce the routing decision in one line before running.
5. **Pause and confirm before long runs** (Path 2, Path 3 paid) UNLESS user signaled batch intent. Batch intent detected by: multiple sources in one invocation, or phrases matching "whole playlist", "full season", "all of these", "do all of X".
6. Override flags are hard — explicit "Path 1 on this panel discussion" produces a single-speaker-shaped output with a warning in frontmatter.

## Phase 3 — Run

**Purpose:** execute the chosen pathway end-to-end including enrichment.

Each pathway is a shell-out to its runner script. SKILL.md reads the matching `references/pathways/P{n}-*.md` file for narrative guidance, then invokes the runner.

**Shared enrichment steps across pathways:**

- **Vocabulary priming** (Path 2 only): build Whisper `initial_prompt` from flattened merged vocab, capped at ~180 tokens
- **Vocabulary post-correction** (both paths): substring replacement, longer variants first, case-insensitive, `\b`-anchored
- **Speaker identification** (Path 2 only): metadata-first → LLM fallback → user override
- **Summary generation**: gpt-4o-mini, one paragraph, from first ~4000 tokens + title
- **Vocabulary candidate discovery**: acronyms, proper nouns, rare unusual words → GPT assessment → `vocab_reviews/` file. Mandatory with natural-language opt-out.
- **LLM quirks review** (Path 2 only): gpt-4o-mini autocorrection with confidence gate (conf ≥0.90, len ≤180)

## Phase 4 — Review

**Hard gates (block success if any fail):**

1. Output file exists at resolved path, non-zero bytes, parseable UTF-8 markdown
2. YAML frontmatter is valid with required fields (`title`, `source`, `transcript_method`, `pathway`, `duration`, `transcribed_at`, `quality`)
3. Markdown body has top-level `#` title, `## Summary` with non-empty content, at least one timestamped segment
4. Summary is 2–8 sentences
5. Pathway-specific checks (P1: no speaker frontmatter, flat timestamp format; P2: host/guest or speakers populated, at least one bolded speaker block, ≥1 diarization labels)

**Soft flags (warnings, non-blocking):**

1. Word count < `duration_minutes * 60` → possible truncation
2. Any `SPEAKER_XX (unknown)` in output → add manually or re-run with `--speakers`
3. `quality: degraded` set → surface `quality_notes`
4. >20 vocab candidates → worth a review pass
5. Heavy vocab correction count (>1 per 100 words) → sanity check
6. Any ambiguous quirks entries → awaiting user review

**Broken output handling:** if a hard gate fails, rename the output file with `.broken.md` suffix. Keeps debuggability while preventing broken outputs from masquerading as good transcripts.

**Completion report format:** see Section 7 of the brainstorming notes — transcript path, duration/word-count, method, quality, speakers list, summary preview, flags section, vocab review pointer, suggested next action.

## Pathway details

### P1 — YouTube Fast

- **When:** single-speaker YouTube content, rough-transcript quality need, <5 min turnaround
- **Preconditions:** yt-dlp, ffmpeg, OPENAI_API_KEY
- **Steps:** metadata → manual subs → auto-captions fallback → Whisper API audio fallback (with `quality: degraded`) → vocab post-correction → summary → vocab candidates → markdown build
- **Skips:** diarization, alignment, quirks review, speaker identification
- **Runner:** `scripts/yt_fast.py`

### P2 — WhisperX Local

- **When:** multi-speaker content, long-run OK, privacy-sensitive, no budget, or YouTube has no subs
- **Preconditions:** yt-dlp, ffmpeg, whisperx, faster-whisper, pyannote.audio, torch, HF_TOKEN, OPENAI_API_KEY, ~3GB disk for model cache + audio
- **Steps:** audio download → vocab prime → WhisperX large-v2 transcribe → alignment → pyannote diarize → overlap-voting speaker assign → merge short blocks → vocab post-correct → metadata speaker research → LLM speaker guess (transcript + title + description together) → map speakers → quirks review with gate → summary → vocab candidates → markdown build
- **Checkpointing:** intermediate state to `.mdpowers/cache/{video_id}/` after each major step. Cache expires after 7 days or on natural-language "clear cache" intent.
- **Critical gotcha:** WhisperX ctranslate2 does NOT support MPS — force CPU even on Apple Silicon. Pyannote itself CAN use MPS.
- **Runner:** `scripts/whisperx_local.py`

### P3 — API Service (stub)

- **Status:** Not wired in v0.1. Stub raises `NotYetImplemented` with actionable error.
- **Roadmap (v0.2):** likely AssemblyAI (~$0.37/hr, diarization, strong accuracy). Implement `api_service.py` with upload/poll/parse, reuse enrichment steps from `lib/`.
- **Runner:** `scripts/api_service.py` (stub)

## Playbooks

### vocabulary-handling.md

**Discovery cascade (precise order):**

1. Start with empty merged vocab
2. Load global master: `$MDPOWERS_VOCAB` env var → `$XDG_DATA_HOME/mdpowers/vocabulary.json` → platform default
3. Walk up from cwd looking for `.mdpowers/vocabulary.*.json` at each level, load all (deepest wins on conflict)
4. `--vocab-overlay <path>` override skips the walk-up, loads only specified file on top of master
5. Merge semantics: overlay keys replace master keys; mistranscription lists REPLACED not unioned (deliberate, overlays can narrow master entries)

**Scope selection when multiple overlays exist at one level:**

- Explicit `use vocabulary from <path>` wins
- Else scope hint matches `_meta.scope` field
- Else directory-name inference
- Else alphabetical with warning

**Priming:** flatten to list, sort by priority (confused terms first, then orgs/people, then concepts, then acronyms), join comma-separated to ~180 tokens. Path 2 only.

**Post-correction:** substring replacement with word boundaries, longer variants first, case-insensitive match, original case preserved on replace. Both paths.

**Candidate discovery:** acronyms (`^[A-Z]{2,6}$`), proper nouns (title-cased mid-sentence, appears ≥1x), rare unusual (lowercase ≥9 chars, appears exactly 1x, not in NLTK fuzzy-matched dict). Three categories → GPT-4o-mini assessment → `vocab_reviews/{date}_{title}_{id}_vocab_review.md`.

**Promotion workflow:**

1. User says "promote X to master" (natural language)
2. Find X in active overlay(s); if not there but in master, report "already in master"; if in neither, report "not found"
3. If in overlay: load master; if already exists there, show three-column diff (master / overlay / merged preview) and ask merge questions; if not, copy verbatim
4. Ask whether to remove from overlay (default no — overlays can duplicate master entries)

### speaker-identification.md

**Three-stage flow:**

1. **Metadata research** (gpt-4o-mini, JSON mode): title + full description only, returns `{host, co_host, guests}`. If populated plausibly, treat as authoritative.
2. **LLM transcript guess** (gpt-4o-mini, strict prompt): only runs if metadata research insufficient. Receives transcript sample (first ~8000 tokens) + title + description. Prompt requires self-introduction OR direct address OR explicit metadata mention. Unresolved labels stay as `SPEAKER_XX (unknown)`.
3. **User override:** `--speakers "A, B, C"` or natural language "speakers are X, Y, Z" bypasses both stages. Order matches diarization label order.

**Mapping:** `map_speakers_by_order()` rewrites segments with real names. Unresolved speakers ship as `SPEAKER_XX (unknown)` in output — honest gaps over hallucinated names.

**Anti-patterns:**

- NEVER fabricate a speaker name from topic context
- NEVER assume first speaker is "the host" without evidence
- NEVER merge two diarized speakers because they "sound similar"

### output-format.md

**YAML frontmatter contract (every transcript):**

```yaml
---
title: "..."
source: "..."
channel: "..."
published: "YYYY-MM-DD"
duration: "HH:MM:SS"
transcript_method: "whisperx-local" | "youtube-manual-subs" | "youtube-auto-captions" | "whisper-api-fallback-no-diarization"
pathway: "P1" | "P2" | "P3"
quality: "full" | "degraded"
quality_notes: null | "explanation..."
vocab_master_version: "YYYY-MM-DD"
vocab_overlay: null | "vocabulary.<scope>.json"
transcribed_at: "YYYY-MM-DDTHH:MM:SSZ"
---
```

**Conditional frontmatter (multi-speaker only):**

```yaml
host: "Name"
co_host: "Name"           # or null
guest: "Name"             # single guest
guests: ["Name", "Name"]  # multiple guests
# OR when roles unclear:
speakers: ["Name", "Name", "SPEAKER_02 (unknown)"]
```

**Markdown body shape (Path 2, with speakers):**

```markdown
# Title

### Description
Original description quoted verbatim

---

## Summary
One paragraph gpt-4o-mini summary

---

**Speaker Name** [HH:MM.ss]

Transcript text...

**Next Speaker** [HH:MM.ss]

...
```

**Markdown body shape (Path 1, no speakers):**

```markdown
# Title

### Description
...

---

## Summary
...

---

[00:00.00] Transcript line...

[02:15.30] Next line...
```

**Output path convention:**

- User-specified output dir used verbatim
- Default: `{cwd}/transcripts/` for generic cwd, `{cwd}` if cwd IS a transcripts directory
- Filename: `{YYYY-MM-DD}_{SafeTitle}_{source_id}.md` (source_id = YouTube video ID or file hash)
- `safe_title()`: strip punctuation, collapse whitespace to underscores, cap 80 chars
- Overwrite conflict: ask overwrite / skip / suffix `_v2`

## Portability — host mode detection

**Detection heuristics in `scripts/lib/host_mode.py`:**

```python
def detect_host_mode():
    if os.environ.get("MDPOWERS_HOST_MODE"):
        return os.environ["MDPOWERS_HOST_MODE"]
    if os.path.exists("/sessions") and "/sessions/" in os.getcwd():
        return "sandbox"
    if os.environ.get("CLAUDECODE") == "1":
        return "local"
    if os.environ.get("CURSOR_AGENT") or os.environ.get("TERM_PROGRAM") == "cursor":
        return "local"
    return "local"
```

**Behavior matrix:**

| Host mode | Path 1 | Path 2 | Setup |
|---|---|---|---|
| `local` | Direct subprocess | Direct subprocess, real GPU/MPS, checkpoint to real disk | Interactive `input()` via `setup_wizard.py` |
| `sandbox` | Direct subprocess inside sandbox (yt-dlp + OpenAI API both work) | **Script emission:** write `run_transcribe_{ts}.sh` to workspace, tell user to run from terminal | Non-interactive: skill drives steps via AskUserQuestion + file tools, follows `references/setup-sandbox.md` |

**Script emission (sandbox + Path 2):**

1. Skill prepares invocation (resolves source, loads vocab, computes output path, determines flags) inside sandbox
2. Reads `.mdpowers/host-path` to translate sandbox mount paths → user-local host paths
3. Writes self-contained shell script to workspace folder with full invocation
4. Surfaces `computer://` link + instructions + expected runtime
5. When user returns after running the script, skill runs Review phase on the resulting file

**Sandbox-mode caching:** enabled, `.mdpowers/cache/{video_id}/` under workspace mount. Auto-added to `.gitignore`. Vocabulary file itself is NOT gitignored — committed as project context.

## Natural-language intent routing

SKILL.md ships with an intent routing table. Examples:

| Phrasing | Action |
|---|---|
| "transcribe <url>" | Default: full Probe → Route → Run → Review |
| "use the fast/local/api pathway" | Override pathway |
| "do this whole playlist / full season / all of these" | Batch mode — skip long-run confirmation |
| "the speakers are X, Y, Z" | `--speakers` override |
| "there are 3 speakers" | `--num-speakers` hint |
| "use vocabulary from <path>" | `--vocab-overlay` override |
| "skip the vocab review" | `vocab_review: skipped` |
| "add X to my vocabulary [as Y] [variants: a, b, c]" | Natural-language vocab add |
| "promote X to master" | Promotion workflow |
| "edit my vocabulary" / "show me my vocab" | Open vocab file, show summary |
| "clear the transcribe cache" | Delete `.mdpowers/cache/*` |
| "clean up broken transcripts" | Delete `*.broken.md` with confirmation |
| "what's my transcribe setup" | Probe and report without transcribing |

Ambiguous intents get one-line clarifying questions before proceeding.

## Setup flow — `/transcribe setup`

Idempotent, nine steps (local mode interactive, sandbox mode driven by skill):

1. **Welcome + detection** — OS, `$XDG_DATA_HOME`, git repo status, existing master/overlays
2. **Master vocabulary setup** — keep/replace/merge if exists, else create from blank/template/import
3. **Project overlay setup** — optional, scoped to git repo name by default, writes `_meta.scope`
4. **Host path capture** (sandbox mode only) — ask for user-local host path, store in `.mdpowers/host-path`
5. **`.gitignore` update** — add `.mdpowers/cache/` if in git repo
6. **Environment variable check** — OPENAI_API_KEY, HF_TOKEN, surface missing with setup guidance
7. **Dependency check + install offer** — three-tier install prompts
8. **WhisperX model prefetch** (only if Path 2 deps installed) — trigger model downloads now instead of lazy
9. **Completion report** — what's ready, what's missing, how to run first transcription

**Sync requirement:** `setup_wizard.py` and `references/setup-sandbox.md` cover the same logic and must stay in sync. Each file has a header comment naming the other as its mirror.

## Script inventory (scripts/)

| File | Lines (est) | Purpose |
|---|---|---|
| `probe.py` | ~150 | Source + env + vocab + host-mode probing |
| `yt_fast.py` | ~250 | Path 1 runner |
| `whisperx_local.py` | ~600 | Path 2 runner (heaviest) |
| `api_service.py` | ~80 | Path 3 stub |
| `setup_wizard.py` | ~250 | Local-mode interactive setup |
| `emit_run_script.py` | ~150 | Sandbox-mode script emitter |
| `install_path2.sh` | ~40 | Heavy deps + WhisperX model prefetch |
| `install_nltk_data.sh` | ~15 | NLTK words corpus download |
| `requirements.txt` | ~8 | Tier 1 core deps |

## Lib inventory (scripts/lib/)

| File | Lines (est) | Purpose |
|---|---|---|
| `__init__.py` | ~5 | Empty package marker |
| `host_mode.py` | ~120 | Detection + path mapping + script emission helpers |
| `vocabulary.py` | ~350 | Load, flatten, prime, correct, discover, promote |
| `speakers.py` | ~300 | Metadata research, LLM guess, overlap assign |
| `diarization_cleanup.py` | ~200 | Merge short blocks, validate counts |
| `ytdlp_helpers.py` | ~250 | Cookie fallback, metadata, subs, audio |
| `markdown_builder.py` | ~300 | Frontmatter, speaker blocks, path resolution |
| `llm_review.py` | ~250 | Summary, quirks review |
| `errors.py` | ~60 | `TranscribeError` + `VocabularyError`, `SpeakerError`, `DiarizationError`, `HostModeError`, `PathwayError` |

**Runner imports are explicit** — no re-exports in `__init__.py`. Reading the top of a runner tells you its full dependency surface.

## Graceful degradation matrix

See brainstorming notes Section 7 for the full matrix. Governing principle: **explicit user pathway override is never silently degraded**. Adaptive routing allows fallback with user confirmation. Every degradation sets `quality: degraded` with `quality_notes` explaining what fell back to what.

Key degradations:

- No subs on YouTube → Whisper API audio fallback (Path 1)
- WhisperX OOM during transcription → retry with `medium` model → fall back to Whisper API chunking (Path 2)
- WhisperX OOM during alignment → segment-level timestamps only, keep speakers (Path 2)
- OPENAI_API_KEY missing → skip summary/candidate-assessment/quirks, keep transcription + vocab correction
- NLTK corpus missing → skip rare-word discovery, keep acronym + proper noun discovery
- Pyannote returns 1 speaker on known-multi → retry with `num_speakers=2`, else surface warning
- Pyannote over-splits → `merge_short_speaker_blocks` auto-heals, surface warning if still over

## Dependencies (three tiers)

**Tier 1 — Core (requirements.txt):**
- yt-dlp, openai, python-dotenv, tiktoken

**Tier 2 — Path 2 heavy (install_path2.sh):**
- whisperx, faster-whisper, pyannote.audio, torch, torchaudio, huggingface_hub, nltk
- Pre-downloads WhisperX large-v2 + alignment model + pyannote speaker-diarization-3.1 (requires HF_TOKEN accepted license)

**Tier 3 — NLTK corpus (install_nltk_data.sh):**
- `python -c "import nltk; nltk.download('words')"` — idempotent, safe to re-run

Setup wizard orchestrates all three interactively.

## Relationship to other mdpowers skills

- **convert** — multi-format converter, the design reference. Established phased-workflow pattern, "guides not rails" principle, recipes catalogue. Transcribe inherits the phased-workflow DNA (compressed to four phases, pathways instead of recipes).
- **clip** — web pages → markdown via Defuddle. Active sibling, no code sharing.
- **pdf-convert** — **deprecated**, functionality subsumed by convert. Deprecation notice to be added during transcribe's implementation cycle.
- **transcribe** — new sibling. No cross-skill hooks in v0.1. Cross-skill auto-suggestion (clip detecting embedded YouTube links, convert routing audio files to transcribe) is v0.2+ direction.

## v0.1 scope boundaries (what's explicitly NOT shipping)

- Local audio/video file sources (v0.2)
- Path 3 API service implementation (v0.2)
- Cross-skill auto-suggestion (v0.2+)
- Automated test suite (v0.2 — "known YouTube video + golden file" approach planned)
- Vimeo, RSS feeds, Podcast Index integration (v0.2+)
- Multi-language support beyond English (v0.2+)
- Cost estimation preview for Path 3 (v0.2)

These belong in ROADMAP.md after spec is saved.

## Open implementation details

Items to resolve during execution — they don't change architecture but need decisions during build:

1. **SKILL.md frontmatter** (name, description, triggers) — draft during implementation, model on convert's SKILL.md
2. **Exception hierarchy surface** — `errors.py` base and subclasses, catch boundary at runner entry points
3. **Setup flow sync mechanism** — header comments in both files cross-referencing, plus a CI check (v0.2) that flags drift
4. **Broken-file cleanup intent** — "clean up broken transcripts" command, confirm before delete
5. **Batch mode detection regex** — precise phrase matching rules
6. **`safe_title()` Unicode handling** — should non-ASCII characters transliterate or get stripped
7. **Cache TTL enforcement** — lazy (check on read) vs. eager (sweep on run)
8. **Probe report serialization format** — dataclass vs. dict, how SKILL.md consumes it

## Watch-item: v0.1 surface area

Acknowledged risk: this is larger than a typical v0.1. Six lib modules, five runners, three playbooks, three pathway files, host mode detection, setup wizard + sandbox equivalent. Mitigations:

- Most code is lifted from working `diarize.py`, not written from scratch
- Helpers have clear single responsibilities (each lib module owns one concern)
- Pathway runners are thin orchestrators over lib calls
- Stub Path 3 keeps the v0.2 roadmap visible without implementation cost
- Checkpointing means a broken run doesn't force re-doing completed steps during iteration

## Acceptance criteria for v0.1

The skill is "done" when all of these pass:

1. `/transcribe setup` runs cleanly in both local mode (on Monty's Mac via Claude Code terminal) and sandbox mode (in Cowork), produces a working master + overlay, captures host path, reports environment state
2. "transcribe <single-speaker-youtube-url>" produces a valid Path 1 transcript with summary and vocab review, in under 5 minutes
3. "transcribe <multi-speaker-podcast-url>" produces a valid Path 2 transcript with diarization, speakers identified, quirks-reviewed, vocab-corrected, summary, vocab candidates
4. In sandbox mode, Path 2 request emits a runnable shell script with correct host paths
5. `--pathway fast` on multi-speaker content produces Path 1-shaped output with appropriate warnings
6. Vocab promotion ("promote X to master") works with diff-on-conflict
7. Broken runs produce `.broken.md` files that don't masquerade as successful transcripts
8. All hard Verify gates pass on happy-path runs; soft flags surface appropriately on known-edge-case runs
9. Path 3 stub raises clear NotImplementedError with roadmap pointer
10. pdf-convert deprecation notice added; CHANGELOG.md + DECISIONS.md + ROADMAP.md updated

---

**Next:** hand off to `superpowers-cowork:writing-plans` for execution plan breakdown, then execute.
