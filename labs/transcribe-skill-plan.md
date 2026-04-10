---
title: Transcribe Skill — Execution Plan
status: draft
version: v0.1
date: 2026-04-09
depends_on: transcribe-skill-spec.md
---

# Transcribe Skill — Execution Plan (v0.1)

> **Approved design:** `labs/transcribe-skill-spec.md`

**Goal:** Build the `transcribe` skill into `mdpowers-plugin/skills/transcribe/` by porting the existing `montymerlinHQ/tools/` transcription system into a host-agnostic plugin skill with YouTube-first v0.1 scope.

**Deliverables:**

- Complete `skills/transcribe/` directory (SKILL.md + 10 references + 9 scripts + 8 lib modules + assets + commands)
- Plugin integration (CHANGELOG, DECISIONS, ROADMAP, README updates + pdf-convert deprecation notice)
- Verification sweep confirming spec coverage

**Estimated total effort:** Multi-session build. Tasks 1–14 (scaffolding + lib + runners + install scripts) form the code core and need to land together. Tasks 15–17 (references) can be written in parallel or sequentially. Tasks 18–20 (SKILL.md + integration + verification) close out.

**Source material being ported:**

- `/sessions/amazing-loving-mccarthy/mnt/montymerlinHQ/tools/diarize.py` (1527 lines — the heavy one)
- `/sessions/amazing-loving-mccarthy/mnt/montymerlinHQ/tools/transcribe.py` (243 lines — Whisper API + chunking)
- `/sessions/amazing-loving-mccarthy/mnt/montymerlinHQ/tools/yt_transcript.py` (234 lines — YouTube subs fetcher)
- `/sessions/amazing-loving-mccarthy/mnt/montymerlinHQ/tools/vocabulary.json` (master vocab schema reference only)

**Target directory:** `/sessions/amazing-loving-mccarthy/mnt/montymerlinHQ/ops/plugins/mdpowers-plugin/skills/transcribe/`

**Host mode during build:** sandbox (Cowork). Files written via `Write`/`Edit`. No subprocess execution of the heavy pipeline during build — verification is syntax-level only.

---

## Phase 1 — Scaffolding (Task 1)

### Task 1: Create skill directory structure and trivial files

**Deliverable:** Empty directory tree + 5 near-trivial files that establish the skill's shape

**Inputs needed:**

- `labs/transcribe-skill-spec.md` sections "Directory structure" and "Script inventory"
- Reference pattern: `skills/convert/` existing structure

**Steps:**

- [ ] **1a** — Create directories via Bash `mkdir -p`:
  - `skills/transcribe/`
  - `skills/transcribe/references/pathways/`
  - `skills/transcribe/references/playbooks/`
  - `skills/transcribe/scripts/lib/`
  - `skills/transcribe/assets/`
  - `skills/transcribe/commands/`
- [ ] **1b** — Write `skills/transcribe/scripts/lib/__init__.py` as empty file with one comment line: `# mdpowers transcribe lib — explicit imports only`
- [ ] **1c** — Write `skills/transcribe/scripts/lib/errors.py` with the exception hierarchy: `TranscribeError` base + `VocabularyError`, `SpeakerError`, `DiarizationError`, `HostModeError`, `PathwayError`, `ProbeError` subclasses. Each ~5 lines, with docstring.
- [ ] **1d** — Write `skills/transcribe/scripts/requirements.txt` with Tier 1 core deps only: `yt-dlp>=2024.1.1`, `openai>=1.12.0`, `python-dotenv>=1.0.0`, `tiktoken>=0.6.0`. Include a commented section listing Tier 2 deps as reference (see spec "Dependencies").
- [ ] **1e** — Write `skills/transcribe/assets/vocabulary.template.json` with the empty-schema template from spec Section 1 (empty category keys, `_meta` block with schema example in comments, `updated: 2026-04-09`).
- [ ] **1f** — Write `skills/transcribe/commands/transcribe-setup.md` — a thin slash-command file that describes what `/transcribe setup` does and points at `scripts/setup_wizard.py` (local mode) or `references/setup-sandbox.md` (sandbox mode). ~30 lines.

**Verification:**

- Run `find skills/transcribe -type d` and confirm all directories exist
- Run `find skills/transcribe -type f` and confirm the 5 files exist
- Open `errors.py` and confirm Python syntax is valid (visual check)
- Open `vocabulary.template.json` and confirm valid JSON (visual + `python -m json.tool`)

---

## Phase 2 — Lib modules (Tasks 2–8)

These are the reusable helpers imported by runners. Most are ports from `diarize.py`; one (`host_mode.py`) is net new. Each task produces one complete, working `.py` file with no placeholder stubs.

### Task 2: Write scripts/lib/host_mode.py (NEW)

**Deliverable:** `skills/transcribe/scripts/lib/host_mode.py` — host mode detection + path mapping

**Inputs needed:**

- Spec section "Portability — host mode detection"
- Spec section "Script emission (sandbox + Path 2)"

**Steps:**

- [ ] **2a** — Write `detect_host_mode() -> str` — returns `"local"` or `"sandbox"` per the heuristics in the spec (`MDPOWERS_HOST_MODE` env override, `/sessions/` path check, `CLAUDECODE` env, `CURSOR_AGENT` / `TERM_PROGRAM=cursor`, default `local`)
- [ ] **2b** — Write `load_host_path(workspace_root: Path) -> Optional[str]` — reads `.mdpowers/host-path` file if present (sandbox mode), returns user-local path string. Returns None if not found.
- [ ] **2c** — Write `save_host_path(workspace_root: Path, host_path: str) -> None` — writes the file during setup
- [ ] **2d** — Write `translate_sandbox_to_host(sandbox_path: str, mount_root: str, host_root: str) -> str` — swap the mount prefix for the host prefix, preserve the rest
- [ ] **2e** — Write `find_workspace_root(cwd: Path) -> Path` — walk up looking for `.mdpowers/` or `.git/`, return the containing directory. Fallback to cwd.
- [ ] **2f** — Add module docstring referencing spec section

**Verification:** Python AST parse via `python -c "import ast; ast.parse(open('scripts/lib/host_mode.py').read())"`. All functions have type hints and docstrings.

### Task 3: Port scripts/lib/ytdlp_helpers.py

**Deliverable:** `skills/transcribe/scripts/lib/ytdlp_helpers.py` — YouTube operations consolidated from two source files

**Inputs needed:**

- `tools/yt_transcript.py` lines 1–234 (all of it)
- `tools/diarize.py` — the yt-dlp auth handling section (search for `_AUTH_ERROR_PATTERNS`, `_yt_run`, `cookie` in the source file)

**Steps:**

- [ ] **3a** — Read `tools/yt_transcript.py` and `tools/diarize.py`, locate all yt-dlp-related functions: `_AUTH_ERROR_PATTERNS`, `_yt_run`, `get_video_info`, `fetch_subtitles`, `parse_json3`, `safe_filename`, and any audio-download helpers
- [ ] **3b** — Port `_AUTH_ERROR_PATTERNS` list verbatim
- [ ] **3c** — Port `_yt_run(args, cookies=None, cookies_from_browser=None)` — subprocess wrapper
- [ ] **3d** — Port `cookie_fallback_chain(url, operation_fn)` — the three-try pattern (no cookies → cookie file → browser cookies). If this doesn't exist as a named function in source, extract from inline calls.
- [ ] **3e** — Port `get_video_info(url)` — `--dump-json` wrapper
- [ ] **3f** — Port `fetch_subtitles(url, tmpdir)` — manual subs first, auto-captions fallback, json3 format
- [ ] **3g** — Port `parse_json3(path)` — json3 → list of `{start, end, text}` segments
- [ ] **3h** — Port `download_audio(url, tmpdir, format='bestaudio')` — for Path 2 and Path 1 Whisper fallback
- [ ] **3i** — Port `safe_filename(title, max_len=80)` — regex sanitize
- [ ] **3j** — Update imports to use relative imports: `from .errors import TranscribeError` where error-raising was inline
- [ ] **3k** — Replace any hardcoded output paths with function parameters

**Verification:** Python AST parse. Compare function count against the target list (9 functions + 1 constant). Grep for `/Users/` or `self/soul-data` in the file — must find zero hits (no personalized paths).

### Task 4: Port scripts/lib/vocabulary.py

**Deliverable:** `skills/transcribe/scripts/lib/vocabulary.py` — full vocab subsystem

**Inputs needed:**

- `tools/diarize.py` vocab section (search for `_flatten_vocab_data`, `_load_vocab_file`, `load_vocabulary`, `apply_vocabulary`, `build_whisper_prompt`, `find_vocabulary_candidates`, `gpt_assess_candidates`, `write_vocabulary_review`, `_load_english_dictionary`, `_in_english_dict`)
- Spec section "vocabulary-handling.md" (describes new behaviors — discovery cascade, promotion)

**Steps:**

- [ ] **4a** — Port `_flatten_vocab_data(data)` verbatim
- [ ] **4b** — Port `_load_vocab_file(vocab_path)` with schema validation (must have `_meta` + ≥1 category)
- [ ] **4c** — Write NEW `load_vocabulary(overlay_path=None, cwd=None)` — implements the discovery cascade from the spec: `$MDPOWERS_VOCAB` → `$XDG_DATA_HOME` → platform default → walk-up overlay loading (deepest wins) → explicit overlay. Returns flattened dict and a `_meta` dict capturing master/overlay versions.
- [ ] **4d** — Port `apply_vocabulary(text, vocab)` verbatim (substring replacement, longest variants first, `\b` word boundaries, case preserving)
- [ ] **4e** — Port `build_whisper_prompt(vocab, token_budget=180)` — priority sort + tiktoken count cap
- [ ] **4f** — Port `_load_english_dictionary()` with NLTK auto-download
- [ ] **4g** — Port `_in_english_dict(word, english_dict)` — suffix-stripping fuzzy match
- [ ] **4h** — Port `find_vocabulary_candidates(segments, known_vocab)` — three-category discovery
- [ ] **4i** — Port `gpt_assess_candidates(client, candidates, title)` — gpt-4o-mini call
- [ ] **4j** — Port `write_vocabulary_review(out_path, title, candidates, gpt_notes, corrections_applied)` — review file writer
- [ ] **4k** — Write NEW `promote_to_master(term, overlay_path, master_path, client=None)` — promotion workflow. If term already in master, raise `VocabularyError` with a dict payload describing the conflict (caller decides diff flow).
- [ ] **4l** — Write NEW `add_term_to_vocab(vocab_path, category, term, mistranscriptions, context)` — natural-language vocab add target
- [ ] **4m** — Replace `import openai` with `from openai import OpenAI` if needed; inject client via parameter rather than global

**Verification:** Python AST parse. Grep for `os.path.expanduser("~")` — master path resolution must use XDG logic, not hardcoded home. Function count matches target (~11 functions).

### Task 5: Port scripts/lib/speakers.py

**Deliverable:** `skills/transcribe/scripts/lib/speakers.py` — speaker identification subsystem

**Inputs needed:**

- `tools/diarize.py` — search for `research_speakers_from_metadata`, `guess_speakers`, `assign_speakers_overlap`, `map_speakers_by_order`
- Spec section "speaker-identification.md"

**Steps:**

- [ ] **5a** — Port `research_speakers_from_metadata(client, title, description, num_speakers)` — gpt-4o-mini JSON mode call, returns `{host, co_host, guests}` dict
- [ ] **5b** — Port `guess_speakers(client, title, description, transcript_sample, num_speakers, speaker_labels)` — strict prompt variant. **NEW:** prompt must include title + description + transcript sample together (spec Section 4 decision). Update the prompt text accordingly.
- [ ] **5c** — Port `assign_speakers_overlap(transcript_segments, diarization, tolerance=5.0)` — overlap voting
- [ ] **5d** — Port `map_speakers_by_order(segments, names)` — for `--speakers` flag bypass
- [ ] **5e** — Write NEW `merge_by_role(speaker_dict)` — resolves host/co_host/guest[s] from metadata dict into frontmatter-ready structure
- [ ] **5f** — Replace any hardcoded ~8000 token count with a `TRANSCRIPT_SAMPLE_TOKENS = 8000` module constant

**Verification:** Python AST parse. Read the `guess_speakers` prompt text and confirm it references title, description, and transcript together.

### Task 6: Port scripts/lib/diarization_cleanup.py

**Deliverable:** `skills/transcribe/scripts/lib/diarization_cleanup.py` — diarization cleanup utilities

**Inputs needed:**

- `tools/diarize.py` — search for `merge_short_speaker_blocks`

**Steps:**

- [ ] **6a** — Port `merge_short_speaker_blocks(segments, min_words=4)` — the 3-pass run collapse
- [ ] **6b** — Write NEW `validate_speaker_count(segments, expected=None) -> Tuple[bool, str]` — sanity check returning `(ok, message)`. If `expected` provided and count mismatches, returns `(False, warning_text)`; otherwise `(True, "")`.

**Verification:** Python AST parse. Function count = 2.

### Task 7: Port scripts/lib/markdown_builder.py

**Deliverable:** `skills/transcribe/scripts/lib/markdown_builder.py` — frontmatter + markdown + path resolution

**Inputs needed:**

- `tools/diarize.py` — search for `build_markdown`, `format_time`
- `tools/yt_transcript.py` — search for `build_markdown`, any path helpers
- Spec "output-format.md" playbook — authoritative frontmatter contract

**Steps:**

- [ ] **7a** — Port `format_time(seconds)` — HH:MM:SS.ss formatter
- [ ] **7b** — Write NEW `build_frontmatter(**fields)` — YAML frontmatter builder enforcing the spec contract. Must include: title, source, channel, published, duration, transcript_method, pathway, quality, quality_notes, vocab_master_version, vocab_overlay, transcribed_at. Optional conditional: host, co_host, guest/guests OR speakers.
- [ ] **7c** — Port + merge `build_markdown` from both source files into two functions:
  - `build_path1_markdown(title, description, summary, segments, frontmatter_dict)` — no speakers, flat `[HH:MM:SS.ss]` prefix lines
  - `build_path2_markdown(title, description, summary, segments, frontmatter_dict)` — bolded speaker blocks
- [ ] **7d** — Write NEW `resolve_output_path(source_id, title, cwd, user_specified=None) -> Path` — implements the spec's path convention (user-specified verbatim, else `{cwd}/transcripts/` or `{cwd}` if cwd already looks like a transcripts dir)
- [ ] **7e** — Write NEW `handle_overwrite_conflict(path) -> Path` — returns either the original path (overwrite approved), None (skip), or a new `_v2`-suffixed path. In sandbox mode, defaults to `_v2` without prompting.
- [ ] **7f** — Write NEW `rename_broken(path: Path) -> Path` — rename failed-verification output with `.broken.md` suffix

**Verification:** Python AST parse. Grep for `self/soul-data` or `podcasts&presentations` — must find zero hits.

### Task 8: Port scripts/lib/llm_review.py

**Deliverable:** `skills/transcribe/scripts/lib/llm_review.py` — summary + quirks review

**Inputs needed:**

- `tools/diarize.py` — search for `generate_summary`, `llm_quirks_review`, `apply_llm_quirk_autocorrections`
- `tools/yt_transcript.py` — alternate `generate_summary` implementation

**Steps:**

- [ ] **8a** — Merge the two `generate_summary` implementations into one canonical `generate_summary(client, title, segments, speaker_names=None)` that handles both pathways. Uses gpt-4o-mini, first ~4000 tokens of transcript + title, returns one paragraph.
- [ ] **8b** — Port `llm_quirks_review(client, title, segments, speaker_names)` verbatim. Returns `{auto_corrections: [...], ambiguous: [...]}`.
- [ ] **8c** — Port `apply_llm_quirk_autocorrections(segments, corrections, conf_threshold=0.90, len_threshold=180)` with the safety gate exactly as in source.
- [ ] **8d** — Write NEW `_clip_to_token_budget(text, max_tokens)` — tiktoken-based truncation helper
- [ ] **8e** — Write NEW `_strip_speaker_blocks_for_prompt(segments)` — serialize segments to a compact prompt-ready string

**Verification:** Python AST parse. Grep for the exact threshold values `0.90` and `180` in the file.

---

## Phase 3 — Runners (Tasks 9–13)

### Task 9: Write scripts/probe.py (NEW)

**Deliverable:** `skills/transcribe/scripts/probe.py` — shared source + environment probe, returns `ProbeReport`

**Inputs needed:**

- Spec "Phase 1 — Probe" section
- `scripts/lib/host_mode.py` (from Task 2)
- `scripts/lib/ytdlp_helpers.py` (from Task 3)
- `scripts/lib/vocabulary.py` (from Task 4)

**Steps:**

- [ ] **9a** — Define `@dataclass ProbeReport` with fields: `sources: List[SourceInfo]`, `env: EnvProbe`, `vocab: VocabProbe`, `host_mode: str`, `workspace_root: Path`. Also define `SourceInfo`, `EnvProbe`, `VocabProbe` dataclasses.
- [ ] **9b** — Write `probe_source(url_or_path: str) -> SourceInfo` — routes to `probe_youtube()` or raises `ProbeError("local files not supported in v0.1")` for local paths.
- [ ] **9c** — Write `probe_youtube(url)` — calls `ytdlp_helpers.get_video_info()`, extracts title/channel/duration/description, detects manual subs + auto captions + auth wall.
- [ ] **9d** — Write `probe_environment() -> EnvProbe` — checks `shutil.which('yt-dlp')`, `shutil.which('ffmpeg')`, tries `importlib.util.find_spec()` for whisperx/pyannote/torch, reads env vars.
- [ ] **9e** — Write `probe_vocabulary(cwd) -> VocabProbe` — walks for overlays, checks master path, counts terms.
- [ ] **9f** — Write `main()` CLI entrypoint — takes source URL(s), prints ProbeReport as JSON.
- [ ] **9g** — Guard with `if __name__ == "__main__"`.

**Verification:** Python AST parse. Run `python scripts/probe.py --help` (if argparse configured) to verify it executes without import errors.

### Task 10: Port scripts/yt_fast.py

**Deliverable:** `skills/transcribe/scripts/yt_fast.py` — Path 1 runner

**Inputs needed:**

- `tools/yt_transcript.py` (main reference, the old Path 1)
- `tools/transcribe.py` (chunking logic for the Whisper API fallback)
- Spec pathway file P1 (not yet written; reference Section 3 of the spec)
- `scripts/lib/` modules from Phase 2

**Steps:**

- [ ] **10a** — Import from `lib`: `vocabulary`, `markdown_builder`, `llm_review`, `ytdlp_helpers`, `errors`
- [ ] **10b** — Write `run(source, out_dir, vocab_overlay=None, skip_vocab_review=False, openai_client=None) -> Path` — the main entry point returning the output file path
- [ ] **10c** — Step 1: fetch metadata via `ytdlp_helpers.get_video_info`
- [ ] **10d** — Step 2: try `fetch_subtitles` (manual → auto); if both fail, set `quality: degraded` and fall back to Whisper API on downloaded audio using chunking logic ported from `tools/transcribe.py` (MAX_BYTES = 24MB, CHUNK_MINUTES = 10)
- [ ] **10e** — Step 3: parse segments via `parse_json3` or assemble from Whisper API responses
- [ ] **10f** — Step 4: load vocab, apply `vocabulary.apply_vocabulary` to each segment text
- [ ] **10g** — Step 5: generate summary via `llm_review.generate_summary`
- [ ] **10h** — Step 6 (unless skipped): `vocabulary.find_vocabulary_candidates` + `gpt_assess_candidates` + `write_vocabulary_review`
- [ ] **10i** — Step 7: build markdown via `markdown_builder.build_path1_markdown`, resolve path via `resolve_output_path`, handle overwrite, write
- [ ] **10j** — Return the output path
- [ ] **10k** — Write `main()` CLI wrapper with argparse (source, --out, --vocab-overlay, --skip-vocab-review, --pathway=fast)
- [ ] **10l** — Guard with `if __name__ == "__main__"`

**Verification:** Python AST parse. Grep for `/Users/` — zero hits. Count `from lib.` imports — expect ≥5.

### Task 11: Port scripts/whisperx_local.py

**Deliverable:** `skills/transcribe/scripts/whisperx_local.py` — Path 2 runner (the heavy one)

**Inputs needed:**

- `tools/diarize.py` (main reference — the entire `process()` orchestrator + `run_whisperx_pipeline()` + torch patch)
- `scripts/lib/` modules from Phase 2
- Spec Path 2 pathway detail + checkpointing spec

**Steps:**

- [ ] **11a** — Port the PyTorch 2.6+ compat patch at module top (`lightning_fabric.utilities.cloud_io._load` monkey-patch)
- [ ] **11b** — Import from `lib`: `vocabulary`, `speakers`, `diarization_cleanup`, `markdown_builder`, `llm_review`, `ytdlp_helpers`, `errors`
- [ ] **11c** — Write checkpoint helpers: `save_checkpoint(cache_dir, name, data)`, `load_checkpoint(cache_dir, name)`, `checkpoint_exists(cache_dir, name)`. JSON-based except for RTTM (diarization output), which is text.
- [ ] **11d** — Write `run(source, out_dir, hf_token, openai_client, ...) -> Path` main entry point
- [ ] **11e** — Step 1: resolve source, determine cache dir at `.mdpowers/cache/{video_id}/`, check for existing checkpoints
- [ ] **11f** — Step 2: `ytdlp_helpers.download_audio` (skip if cached)
- [ ] **11g** — Step 3: load vocab, build Whisper `initial_prompt` via `vocabulary.build_whisper_prompt`
- [ ] **11h** — Step 4: `run_whisperx_pipeline(audio, hf_token, num_speakers, prompt)` — WhisperX large-v2 + alignment. **CRITICAL:** force CPU for WhisperX ctranslate2 even on Apple Silicon; pyannote can use MPS. Save checkpoint after each sub-step.
- [ ] **11i** — Step 5: `pyannote` diarization (if not already from WhisperX `DiarizationPipeline`)
- [ ] **11j** — Step 6: `speakers.assign_speakers_overlap`
- [ ] **11k** — Step 7: `diarization_cleanup.merge_short_speaker_blocks`
- [ ] **11l** — Step 8: `vocabulary.apply_vocabulary` post-correction
- [ ] **11m** — Step 9: `speakers.research_speakers_from_metadata` → `speakers.guess_speakers` if insufficient → `speakers.map_speakers_by_order`
- [ ] **11n** — Step 10: `llm_review.llm_quirks_review` → `apply_llm_quirk_autocorrections`
- [ ] **11o** — Step 11: `llm_review.generate_summary`
- [ ] **11p** — Step 12 (unless skipped): vocab candidate discovery
- [ ] **11q** — Step 13: `markdown_builder.build_path2_markdown` → resolve path → write
- [ ] **11r** — Wrap the whole pipeline in try/except that on OOM retries with `medium` model (step 11h) or falls back to Whisper API chunking from `yt_fast.py` logic
- [ ] **11s** — Write `main()` CLI with argparse (source, --out, --vocab-overlay, --speakers, --num-speakers, --skip-vocab-review, --cookies-file, --cookies-from-browser)
- [ ] **11t** — Guard with `if __name__ == "__main__"`

**Verification:** Python AST parse. Grep for `MPS` or `mps` — expect at least one hit that's an explicit CPU fallback comment. Grep for `checkpoint` — expect ≥5 hits. Grep for `/Users/` — zero hits.

### Task 12: Write scripts/api_service.py stub

**Deliverable:** `skills/transcribe/scripts/api_service.py` — ~80-line stub

**Inputs needed:** Spec Section 3 "P3 — API Service stub" content

**Steps:**

- [ ] **12a** — Write module docstring explaining this is the v0.2 Path 3 stub
- [ ] **12b** — Define `class NotYetImplemented(NotImplementedError)` with custom message
- [ ] **12c** — Write `run(source, **kwargs)` that raises `NotYetImplemented` with the exact message from spec ("Path 3 (API service) is not yet implemented in v0.1...")
- [ ] **12d** — Write `main()` that prints the unsupported message to stderr and exits 1
- [ ] **12e** — Guard with `if __name__ == "__main__"`

**Verification:** Python AST parse. File is <100 lines. Calling `python scripts/api_service.py` prints the expected error and exits non-zero.

### Task 13: Write install scripts (install_path2.sh + install_nltk_data.sh)

**Deliverable:** Two shell scripts with executable bits

**Inputs needed:** Spec "Dependencies (three tiers)" section

**Steps:**

- [ ] **13a** — Write `scripts/install_path2.sh`:
  - Shebang `#!/usr/bin/env bash`, `set -e`
  - Echo "Installing Path 2 heavy dependencies..."
  - Detect platform (Darwin vs Linux) — Darwin ARM uses `torch` default wheel; Linux may need CUDA variant
  - `pip install --break-system-packages whisperx faster-whisper pyannote.audio torch torchaudio huggingface_hub nltk`
  - Echo "Prefetching WhisperX large-v2 model..."
  - Run `python -c "import whisperx; whisperx.load_model('large-v2', device='cpu', compute_type='float32')"` — triggers model download
  - Echo "Prefetching pyannote speaker-diarization-3.1 (requires HF_TOKEN)..."
  - If `HF_TOKEN` unset, print warning and skip this step
  - Else run `python -c "from pyannote.audio import Pipeline; import os; Pipeline.from_pretrained('pyannote/speaker-diarization-3.1', use_auth_token=os.environ['HF_TOKEN'])"`
  - Echo "Done. Run install_nltk_data.sh next to download the NLTK words corpus."
- [ ] **13b** — Write `scripts/install_nltk_data.sh`:
  - Shebang, `set -e`
  - Echo "Downloading NLTK words corpus..."
  - Run `python -c "import nltk; nltk.download('words')"`
  - Echo "Done."
- [ ] **13c** — Make both executable via file permission change documented in task (Bash `chmod +x` won't work in sandbox; leave a note that the user needs to `chmod +x` on first local run)

**Verification:** Run `bash -n scripts/install_path2.sh` and `bash -n scripts/install_nltk_data.sh` for syntax check.

---

## Phase 4 — Setup scripts (Task 14)

### Task 14: Write scripts/setup_wizard.py + scripts/emit_run_script.py

**Deliverable:** Two NEW scripts

**Inputs needed:**

- Spec "Setup flow — /transcribe setup" section (9 steps)
- Spec "Portability — host mode detection" section (script emission)
- `scripts/lib/host_mode.py` (Task 2)
- `scripts/lib/vocabulary.py` (Task 4) — for template/import handling
- `assets/vocabulary.template.json` (Task 1)

**Steps for `setup_wizard.py` (~250 lines):**

- [ ] **14a** — Import host_mode, vocabulary modules
- [ ] **14b** — Write `step1_detect()` — detect OS, XDG path, cwd git repo status, existing master/overlays. Returns a dict.
- [ ] **14c** — Write `step2_master_vocab(detection)` — prompt keep/replace/merge if master exists, else prompt blank/import/template
- [ ] **14d** — Write `step3_project_overlay(detection)` — prompt for scope name, write overlay from template, add `_meta.scope`
- [ ] **14e** — Write `step4_host_path(detection)` — sandbox mode only: prompt for user-local host path, save via `host_mode.save_host_path`
- [ ] **14f** — Write `step5_gitignore(detection)` — add `.mdpowers/cache/` to `.gitignore` if in git repo, create gitignore if missing
- [ ] **14g** — Write `step6_env_check()` — check OPENAI_API_KEY, HF_TOKEN, surface missing with setup pointers (no file writes)
- [ ] **14h** — Write `step7_deps_check()` — probe Tier 1/2/3, offer interactive install via `subprocess.call(['bash', 'scripts/install_path2.sh'])`
- [ ] **14i** — Write `step8_model_prefetch()` — only if Tier 2 just installed, call install_path2.sh's prefetch logic (or rely on install_path2.sh to do it inline)
- [ ] **14j** — Write `step9_completion_report()` — print the formatted completion report per spec
- [ ] **14k** — Write `main()` that runs all 9 steps in order, with a top-of-file header comment: `# SYNC NOTE: This file mirrors references/setup-sandbox.md. Changes here must be reflected there.`

**Steps for `emit_run_script.py` (~150 lines):**

- [ ] **14l** — Import host_mode
- [ ] **14m** — Write `emit_run_script(pathway, source, out_path, vocab_overlay, num_speakers, speakers_override, workspace_root) -> Path` — builds the shell script content and writes it to the workspace folder with timestamp
- [ ] **14n** — Script template:
  ```bash
  #!/bin/bash
  # Generated by mdpowers transcribe skill on {timestamp}
  # Run this from your local terminal to execute Path {N} transcription
  set -e
  cd "{host_plugin_dir}"
  python scripts/{runner}.py "{source}" --out "{host_out_dir}" [flags]
  echo "Done. Transcript at: {host_out_dir}"
  ```
- [ ] **14o** — Write `build_chat_message(script_path_sandbox, script_path_host, expected_runtime) -> str` — returns the surfaced message template with `computer://` link placeholder
- [ ] **14p** — Write `main()` for direct invocation (for testing)

**Verification:** Python AST parse both files. Grep `setup_wizard.py` for the sync note comment.

---

## Phase 5 — Reference files (Tasks 15–17)

### Task 15: Write pathway reference files (P1, P2, P3)

**Deliverable:** Three markdown files in `skills/transcribe/references/pathways/`

**Inputs needed:** Spec "Pathway details" section

**Steps:**

- [ ] **15a** — Write `P1-youtube-fast.md` using the structure from spec Section 3 (When to use / Preconditions / Steps / What this pathway skips / Success criteria / Failure modes & handling / Runner). ~150 lines.
- [ ] **15b** — Write `P2-whisperx-local.md` with same structure, plus the full gotcha list (MPS, HF_TOKEN, OOM handling, checkpoint cache). ~200 lines.
- [ ] **15c** — Write `P3-api-service.md` as the documented stub with status, candidate services, v0.1 behavior, v0.2 implementation plan. ~80 lines.

**Verification:** Each file has the required section headers. `wc -l` shows line counts within expected ranges.

### Task 16: Write playbook reference files (vocab, speakers, output)

**Deliverable:** Three markdown files in `skills/transcribe/references/playbooks/`

**Inputs needed:** Spec "Playbooks" section

**Steps:**

- [ ] **16a** — Write `vocabulary-handling.md` — discovery cascade, scope selection, priming, post-correction, candidate discovery, promotion workflow. Include the ordered numbered cascade from the spec. ~220 lines.
- [ ] **16b** — Write `speaker-identification.md` — three-stage flow, mapping, frontmatter shape, anti-patterns. Include the strict-prompt requirements explicitly. ~180 lines.
- [ ] **16c** — Write `output-format.md` — YAML frontmatter contract (required + conditional), markdown body shapes for Path 1 vs Path 2, output path convention, overwrite conflict handling, broken-output handling. ~200 lines.

**Verification:** Each file has the required sections. Grep each for key terms from the spec (e.g., `output-format.md` must contain `transcript_method`, `quality_notes`).

### Task 17: Write remaining reference files (environments, setup, setup-sandbox, anti-patterns)

**Deliverable:** Four markdown files in `skills/transcribe/references/`

**Inputs needed:** Spec "Setup flow" + "Portability" sections, plus new content for environments and anti-patterns

**Steps:**

- [ ] **17a** — Write `environments.md` — the probe + dependency matrix. Per-pathway dependency lists, platform notes (Darwin vs Linux CUDA vs CPU), env var requirements, install commands. ~150 lines.
- [ ] **17b** — Write `setup.md` — the local-mode interactive setup walkthrough. Nine steps described as narrative for human reference, pointing at `scripts/setup_wizard.py` as the implementation. ~200 lines.
- [ ] **17c** — Write `setup-sandbox.md` — the sandbox-mode setup playbook. Same nine steps, structured for chat-UI-driven execution via AskUserQuestion + file tools. Top-of-file sync note: `<!-- SYNC NOTE: This file mirrors scripts/setup_wizard.py. Changes here must be reflected there. -->`. ~200 lines.
- [ ] **17d** — Write `anti-patterns.md` — hard rails list: never fabricate speaker names, never silently degrade on explicit override, never skip Review phase, never commit vocab cache files, MPS+WhisperX ctranslate2 gotcha, etc. ~100 lines.

**Verification:** All four files exist. `setup-sandbox.md` contains the sync note comment. `anti-patterns.md` contains at least 8 distinct rules.

---

## Phase 6 — SKILL.md orchestrator (Task 18)

### Task 18: Write skills/transcribe/SKILL.md

**Deliverable:** The skill's top-level orchestration document

**Inputs needed:**

- Spec sections "Phase 1–4", "Natural-language intent routing"
- `skills/convert/SKILL.md` as format reference
- All files from Tasks 1–17 so the SKILL.md can reference them correctly

**Steps:**

- [ ] **18a** — Write YAML frontmatter: `name: transcribe`, `description:` (mandatory triggers: "transcribe", ".mp3", "youtube url", "podcast transcript", "transcribe this video", "get a transcript", "diarize"), `location` pointer. Model on convert's SKILL.md frontmatter.
- [ ] **18b** — Write opening section: "What this skill does" — 2 paragraphs
- [ ] **18c** — Write "When to use / when NOT to use" — bullet lists
- [ ] **18d** — Write "The four phases" — ordered list with 1-2 sentences each, pointing at references for detail
- [ ] **18e** — Write "Pathways at a glance" table with P1/P2/P3 summary
- [ ] **18f** — Write "Intent routing" section — the full natural-language table from spec Section 6
- [ ] **18g** — Write "Host mode handling" — brief explainer + pointer to `scripts/lib/host_mode.py` and `references/setup-sandbox.md`
- [ ] **18h** — Write "Vocabulary — discovery cascade" — brief explainer + pointer to `references/playbooks/vocabulary-handling.md`
- [ ] **18i** — Write "Speakers — identification flow" — brief explainer + pointer to playbook
- [ ] **18j** — Write "Output format contract" — pointer to playbook, short frontmatter example
- [ ] **18k** — Write "Failure handling + degradation" — pointer to degradation matrix in relevant playbook, enumerate the most common failures
- [ ] **18l** — Write "Verify phase — success criteria" — the hard gates + soft flags, compact list
- [ ] **18m** — Write "Before you run — checklist" — 5–10 items the skill should confirm before invoking a runner
- [ ] **18n** — Write "Anti-patterns" — pointer to `references/anti-patterns.md` + top 5 most important rules inline
- [ ] **18o** — Write "References index" — list of all reference files with one-line descriptions

**Verification:** YAML frontmatter parses. File length 250–400 lines. Every reference file written in Tasks 15–17 is linked from SKILL.md. Grep for `<!-- TODO -->` and similar placeholders — zero hits.

---

## Phase 7 — Plugin integration (Task 19)

### Task 19: Update plugin-level files

**Deliverable:** Updates to 6 existing plugin files + 1 deprecation notice

**Inputs needed:**

- Existing `CHANGELOG.md`, `DECISIONS.md`, `ROADMAP.md`, `README.md`, `COMPATIBILITY.md`, `.claude-plugin/plugin.json` (or equivalent)
- `skills/pdf-convert/SKILL.md` (to add deprecation notice)
- Spec "Relationship to other mdpowers skills" section

**Steps:**

- [ ] **19a** — Read `.claude-plugin/plugin.json` (or equivalent manifest); if skills are listed explicitly, add `transcribe` to the list. If skills are auto-discovered, skip this subtask.
- [ ] **19b** — Add `CHANGELOG.md` entry at the top: version bump + narrative paragraph explaining transcribe addition + pdf-convert deprecation + host-mode pattern introduction
- [ ] **19c** — Add `DECISIONS.md` entry D006 with Context / Decision / Rationale / Outcome / Implications format, referencing `labs/transcribe-skill-spec.md` as the full design source
- [ ] **19d** — Add `ROADMAP.md` v0.2 items: local audio/video files, Path 3 API service implementation (likely AssemblyAI), cross-skill auto-suggestion, automated test suite, pdf-convert removal
- [ ] **19e** — Update `README.md` skills section to list transcribe alongside convert and clip, with a one-line description. Mark pdf-convert as `(deprecated — use convert)`.
- [ ] **19f** — Update `COMPATIBILITY.md` if it enumerates per-skill compatibility — add transcribe row noting local mode + sandbox mode support with Path 2 caveat
- [ ] **19g** — Prepend deprecation notice to `skills/pdf-convert/SKILL.md` frontmatter and a new opening section: "DEPRECATED: Functionality subsumed by the `convert` skill. This skill will be removed in v0.4. See `references/migration-to-convert.md` for migration guidance." (Don't write migration-to-convert.md unless it already exists — just reference it.)

**Verification:** Read each modified file post-edit and confirm the changes landed. `grep -l transcribe skills/ --include=SKILL.md -r` shows only `skills/transcribe/SKILL.md` (plus any README cross-references). `grep deprecated skills/pdf-convert/SKILL.md` finds the notice.

---

## Phase 8 — Verification (Task 20)

### Task 20: Verification sweep

**Deliverable:** Written verification report confirming spec coverage

**Inputs needed:**

- All files produced by Tasks 1–19
- `labs/transcribe-skill-spec.md` as the checklist source

**Steps:**

- [ ] **20a** — File existence sweep: run `find skills/transcribe -type f` and compare against the directory structure in spec Section 1. Every expected file must exist.
- [ ] **20b** — Python syntax sweep: for every `.py` file in `scripts/` and `scripts/lib/`, run `python -c "import ast; ast.parse(open(PATH).read())"`. All must parse cleanly.
- [ ] **20c** — Shell syntax sweep: run `bash -n` on both install scripts.
- [ ] **20d** — JSON syntax sweep: run `python -m json.tool < assets/vocabulary.template.json` — must parse.
- [ ] **20e** — YAML frontmatter sweep: parse the frontmatter of every `.md` file in the skill. Each must have valid YAML.
- [ ] **20f** — Personalization leak check: grep the entire skill directory for `/Users/`, `self/soul-data`, `podcasts&presentations`, `montybryant`, `refi-dao-koi`. Expected zero hits (except possibly in reference doc examples, which must be flagged and anonymized if found).
- [ ] **20g** — Spec coverage cross-check: for each acceptance criterion in spec Section "Acceptance criteria for v0.1", identify which files implement it and note as a table entry.
- [ ] **20h** — Open implementation details check: for each of the 8 "Open implementation details" in the spec, confirm it was resolved during build (or explicitly deferred to a v0.1.1 patch task, logged in DECISIONS.md)
- [ ] **20i** — Write verification report to `labs/transcribe-skill-verification.md` with: file inventory + sizes, any syntax failures, any leaks found, spec coverage table, outstanding known gaps for a fast-follow patch
- [ ] **20j** — Report outstanding items (if any) to the user via chat, with pointers to where they live in the code and what would need to happen to close them

**Verification:** The verification report file exists, has no `FAIL` or `GAP` sections larger than an agreed-upon threshold (discussed with user after this task completes).

---

## Verification Checklist (plan-level)

- [ ] Every requirement from the approved design is covered by at least one task (see Task 20g cross-check)
- [ ] No task contains placeholders or vague instructions
- [ ] Every task has a verification step
- [ ] Dependencies are marked (Phase 2 before Phase 3, Phase 5 can be partially parallel, Phase 6 depends on 1–5, Phase 7 is independent of 6, Phase 8 depends on everything)
- [ ] Total scope matches the multi-session build discussed during brainstorming

## Sequencing and dependencies

```
Phase 1 (Task 1) — Scaffolding — no deps
    ↓
Phase 2 (Tasks 2–8) — Lib modules — depends on Task 1
    ↓
Phase 3 (Tasks 9–13) — Runners + install — depends on Phase 2
    ↓
Phase 4 (Task 14) — Setup scripts — depends on Phase 2 (host_mode, vocabulary)

Phase 5 (Tasks 15–17) — References — depends only on Task 1 (directory exists). Can run in parallel with Phases 2–4 if desired.

Phase 6 (Task 18) — SKILL.md — depends on Phases 2–5 (needs to reference real files)

Phase 7 (Task 19) — Plugin integration — depends on Phase 1 minimum (skill dir exists), Phase 6 recommended (so README description is accurate)

Phase 8 (Task 20) — Verification sweep — depends on all prior phases
```

## Known deferred items (not blocking v0.1 ship)

These are called out in the spec as v0.2+ and are intentionally NOT in this plan:

- Local audio/video file source support
- Path 3 (API service) actual implementation
- Automated test suite
- Cross-skill auto-suggestion hooks
- Multi-language support beyond English
- Cost estimation preview for Path 3

These land in ROADMAP.md per Task 19d.
