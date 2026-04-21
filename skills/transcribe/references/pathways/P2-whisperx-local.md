# WhisperX Local Full-Pipeline Pathway

## When to Use This Pathway

**P2-whisperx-local** is the right choice when:

- You need **full control over transcription quality**, speaker diarization, and alignment
- Source is **local audio/video file** or **YouTube URL** (download locally first)
- You have **sufficient compute** (3–30GB RAM depending on model size; GPU strongly preferred)
- You accept **longer turnaround** (5–60 minutes depending on content length and hardware)
- You require **reproducibility** — local cache, no external API dependencies
- Content has **multiple speakers** requiring accurate boundary detection and assignment
- You want **alignment** at word or phoneme level for detailed analysis

This pathway is **not** recommended for:
- Quick turnaround (<5 minutes) on single-speaker content
- Constrained compute environments (no GPU, limited RAM)
- Users without terminal comfort or Python environment experience
- Scenarios where internet connectivity is preferred to local processing

## Preconditions

**All of the following must be present before starting P2:**

### Required Executables & Libraries

- **yt-dlp** (audio download from YouTube; if YouTube source used)
- **ffmpeg** (audio/video format conversion and preprocessing)
- **whisperx** Python package (main transcription pipeline; install: `pip install git+https://github.com/m-bain/whisperx.git`)
- **faster-whisper** Python package (underlying Whisper model runner; auto-installed with whisperx, but verify)
- **pyannote.audio** Python package (speaker diarization; install: `pip install pyannote.audio`)
- **torch** (PyTorch; CPU or GPU. GPU strongly recommended for speed)

### Environment & Credentials

- **HF_TOKEN** environment variable set — Hugging Face API token with **pyannote.audio license accepted**
  - Get token from https://huggingface.co/settings/tokens
  - Accept license for https://huggingface.co/pyannote/speaker-diarization-3.1 and https://huggingface.co/pyannote/segmentation-3.0
  - Test: `huggingface-cli login` or set `HF_TOKEN=hf_...` directly
- **OPENAI_API_KEY** (optional; for fallback to OpenAI Whisper model if local model fails)

### Hardware & Storage

- **Disk space:** ~3GB minimum for model downloads (faster-whisper-base ~1.5GB, pyannote ~400MB, cache)
- **RAM:** 8GB minimum (base model), 16GB+ recommended for large models or long content
- **GPU:** Highly recommended (NVIDIA CUDA 11.8+, Apple Metal Performance Shaders on macOS, or AMD ROCm)
- **Runtime expectation:**
  - Short clips (5 min): 2–5 minutes
  - Medium content (30 min): 15–30 minutes
  - Long form (2+ hours): 60+ minutes (depends heavily on GPU)

## Steps

1. **Probe environment and validate preconditions** — Run dependency check: ffmpeg, yt-dlp (if needed), whisperx, faster-whisper, pyannote, torch. Test HF_TOKEN by querying Hugging Face API. List available GPU devices (CUDA, MPS, ROCm, CPU fallback). Cache estimated model sizes against available disk.

2. **Resolve audio source** — If YouTube URL: use yt-dlp to download audio (opus, 128kbps, save to `.mdpowers/cache/{video_id}/audio.opus`). If local file: validate format (mp3, m4a, wav, flac, opus) and convert to 16kHz mono WAV using ffmpeg for consistency.

3. **Initialize cache directory** — Create `.mdpowers/cache/{content_id}/` with metadata file. Log start time, source, model choices. This directory will hold checkpoints (stage names below).

4. **Transcription stage (Whisper)** — Run whisperx (or faster-whisper wrapper) with model selection (tiny, base, small, medium, large; default: base). Specify language (auto-detect or user preference). Output: JSON with text, segment timestamps [start, end in float seconds], confidence scores. Save to `.mdpowers/cache/{content_id}/01_transcription.json`. **CHECKPOINT 1.**

5. **Alignment stage (ctranslate2)** — Feed transcription JSON to whisperx alignment module (uses stable-ts for word-level timing). Produces word-level timestamps. Save to `.mdpowers/cache/{content_id}/02_alignment.json`. **CHECKPOINT 2.**

6. **Diarization stage (pyannote.audio)** — Initialize pyannote speaker segmentation + clustering model. Process audio, detect speaker change boundaries. Output: speaker labels per segment (e.g., SPEAKER_00, SPEAKER_01, etc.). Merge adjacent same-speaker segments. Save diarization output to `.mdpowers/cache/{content_id}/03_diarization.json`. **CHECKPOINT 3.**

7. **Merge diarization with transcript** — Match diarization speaker labels to transcript segments by timestamp overlap. Assign speaker to each transcript segment. Handle edge cases: segment straddles speaker boundary (split or assign majority speaker). Save merged to `.mdpowers/cache/{content_id}/04_merged.json`. **CHECKPOINT 4.**

8. **Speaker identification & mapping** — If metadata available (user-provided --speakers, or metadata research enabled): map SPEAKER_XX labels to names. Otherwise leave as SPEAKER_00, SPEAKER_01, etc. Save speaker map to `.mdpowers/cache/{content_id}/05_speaker_map.json`. **CHECKPOINT 5.**

9. **Vocabulary priming (if overlay provided)** — Flatten vocabulary overlay to list, sort by priority (confused terms first, then orgs/people, then concepts, then acronyms). Cap at 180 tokens. Feed to Whisper via prompt (if supported by model runner). This increases likelihood of correct recognition for domain-specific terms. Verify priming was applied in checkpoint.

10. **Post-hoc correction (vocabulary overlay)** — Iterate through merged transcript. For each vocabulary term in overlay: use longest-variant-first, case-insensitive word-boundary matching to replace mistranscribed text with canonical form. Preserve original case of surrounding context. Log corrections applied.

11. **Segment-level timestamp formatting** — Convert floating-point seconds to [HH:MM.ss] format for display. Verify monotonicity (start < end, segments don't overlap). Build speaker blocks: `**SPEAKER_NAME** [HH:MM.ss]` followed by segment text.

12. **Assemble frontmatter** — Create YAML frontmatter with all required and conditional fields. transcript_method: whisperx_local. pathway: P2. quality: high (assuming no Whisper fallback used). vocab_master_version and vocab_overlay: note which versions were applied. transcribed_at: ISO 8601 timestamp.

13. **Build markdown body** — For each speaker/timestamp block: bold speaker name, timestamp in brackets, followed by segment text. Preserve paragraph breaks between speaker turns. Handle overlapping or simultaneous speech (mark as [OVERLAP] or merge intelligently).

14. **Perform quirks review** — Optional: scan transcript for obvious errors (homophones, garbled words, confidence < threshold). Flag for user review. Suggest corrections based on context + vocabulary overlay.

15. **Validate output markdown** — Ensure frontmatter is valid YAML. All timestamps are [HH:MM.ss] and monotonic. No duplicate consecutive lines. Markdown renders without syntax errors.

16. **Write output file** — Save to user-specified path or default convention `{cwd}/transcripts/{YYYY-MM-DD}_{SafeTitle}_{source_id}.md`. Confirm before overwriting existing file.

17. **Clean up cache (optional)** — User can choose to: keep entire cache (reproducible, ~500MB–2GB), keep only checkpoints (metadata, ~10MB), or delete (free space). Default: keep.

18. **Final report** — Log: source, duration, model used, alignment quality, speaker count, vocabulary corrections made, cache location, total runtime.

## What This Pathway Does NOT Skip

Unlike P1, P2 performs **all** enrichment steps:

- ✓ **Diarization** — Full speaker identification and boundary detection
- ✓ **Alignment** — Word-level and phoneme-level timestamps (ctranslate2)
- ✓ **Quirks review** — Confidence scoring, optional manual review suggestions
- ✓ **Vocabulary enrichment** — Master + overlay priming and post-hoc correction
- ✓ **Speaker identification** — Metadata research, LLM guess, optional user override
- ✓ **Reproducibility** — Full checkpoint cache, model selection logged, hash of inputs

## Success Criteria

- ✓ All five checkpoints created in `.mdpowers/cache/{content_id}/`
- ✓ Frontmatter valid YAML with required fields
- ✓ Markdown body has at least one speaker block with timestamp
- ✓ All timestamps are [HH:MM.ss] format, monotonic, non-overlapping
- ✓ Speaker labels map to actual speaker names or numbered SPEAKER_XX labels
- ✓ No vocabulary corrections introduced hallucinated text
- ✓ Output file is valid markdown
- ✓ Cache metadata shows successful completion

## Failure Modes & Handling

### PyTorch 2.6 `weights_only` Incompatibility

**Symptom:** `_pickle.UnpicklingError: Weights only load failed... GLOBAL omegaconf.listconfig.ListConfig was not an allowed global` when loading pyannote VAD or segmentation checkpoints.

**Root cause:** PyTorch 2.6 changed `torch.load` to default `weights_only=True`. This breaks older pyannote/omegaconf model checkpoints that serialised non-Tensor Python objects. **Two patches are required** — applying only one still fails.

**Fix (apply both before importing whisperx or pyannote):**

```python
# Patch 1: register omegaconf types as safe globals (PyTorch 2.6+)
try:
    import torch
    import omegaconf.listconfig
    import omegaconf.dictconfig
    torch.serialization.add_safe_globals([
        omegaconf.listconfig.ListConfig,
        omegaconf.dictconfig.DictConfig,
    ])
except Exception as e:
    print(f"[patch] safe_globals failed (non-fatal): {e}", file=sys.stderr)

# Patch 2: force weights_only=False inside lightning_fabric's checkpoint loader
try:
    from lightning_fabric.utilities import cloud_io as _lf_io
    import torch as _t
    def _patched_lf_load(path_or_url, map_location=None, **kwargs):
        kwargs["weights_only"] = False
        return _t.load(path_or_url, map_location=map_location, **kwargs)
    _lf_io._load = _patched_lf_load
except Exception as e:
    print(f"[patch] lightning_fabric patch failed (non-fatal): {e}", file=sys.stderr)
```

These patches must be applied **before** `import whisperx` or any pyannote import.

**Also see:** `scripts/whisperx_local.py` — both patches are applied in the `_apply_torch_compat_patches()` function at the top of the runner.

**Discovery context:** Encountered 2026-04-15 on Python 3.9 + PyTorch 2.6 + pyannote.audio 3.3 on macOS. Patch 1 alone was insufficient; Patch 2 (lightning_fabric) was the missing piece. The `whisperx_patched.py` workaround file in `/tmp` was the minimum reproducible test case that confirmed both patches together work.

---

### Buzzsprout / Signed CDN Audio Download Fails

**Symptom:** `curl https://www.buzzsprout.com/.../.mp3` returns a 4.4KB HTML page instead of audio. Or: downloading the redirect URL directly returns a 403 or partial file.

**Root cause:** Buzzsprout serves podcast MP3s via signed CloudFront CDN URLs that expire within seconds. A two-step approach (get redirect URL → download separately) fails because the signed URL has already expired by the time the second request fires. The CDN also checks `User-Agent` and `Referer` headers.

**Fix:** Use a single `curl -L` that follows all redirects in one command, with browser-mimicking headers:

```bash
curl -L \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Referer: https://www.buzzsprout.com/" \
  -H "Accept: audio/mpeg, audio/*, */*" \
  -o output.mp3 \
  "https://www.buzzsprout.com/SHOW_ID/EPISODE_ID.mp3"
```

The `-L` flag follows all redirects. The headers prevent CDN bot-detection. The full signed URL chain is followed in one TCP session before the signature window closes.

**This pattern applies broadly** to any podcast CDN that uses signed URLs (Anchor.fm/Spotify RSS, Buzzsprout, SoundOn, etc.). If a direct CDN URL doesn't work, obtain the enclosure URL from the RSS feed rather than the episode page — RSS enclosure URLs are the canonical stable form.

---

### WhisperX Not Installed or Import Fails

**Symptom:** `ModuleNotFoundError: No module named 'whisperx'` or version mismatch.

**Handling:**
1. Check installed version: `pip list | grep whisperx`
2. If missing: Install from github: `pip install git+https://github.com/m-bain/whisperx.git`
3. If version mismatch: Upgrade: `pip install --upgrade git+https://github.com/m-bain/whisperx.git`
4. Re-run dependency check before attempting transcription.
5. If still failing: Fall back to pure faster-whisper (no alignment) with degraded quality warning.

### HF_TOKEN Missing or Invalid

**Symptom:** `PermissionError: You need to pass `use_auth_token` for pyannote.audio` or 401 Unauthorized from Hugging Face.

**Handling:**
1. Check if HF_TOKEN set: `echo $HF_TOKEN` (should output hf_...)
2. If unset: Prompt user to set: `export HF_TOKEN=<your_token>` or set in .env
3. If invalid: Regenerate token at https://huggingface.co/settings/tokens
4. Ensure license accepted: https://huggingface.co/pyannote/speaker-diarization-3.1
5. Test with: `huggingface-cli whoami`
6. If user refuses to set token: Skip diarization, use SPEAKER_00 labels only, quality: degraded.

### MPS / CUDA Device Detection Fails

**Symptom:** PyTorch detects GPU but WhisperX or faster-whisper fails with device mismatch errors.

**CRITICAL — Apple Silicon (MPS):** WhisperX's ctranslate2 dependency **DOES NOT support MPS**. Must force CPU for transcription/alignment, even on Apple Silicon.

**Handling:**
1. Detect device: `torch.cuda.is_available()` (CUDA), `torch.backends.mps.is_available()` (MPS), else CPU.
2. If MPS detected:
   - ⚠️ **CRITICAL:** Set `CUDA_VISIBLE_DEVICES=""` and `TORCH_DEVICE=cpu` to force CPU for whisperx
   - ✓ Pyannote CAN use MPS; set `HF_DEVICE=mps` for pyannote to run on GPU
   - Log: "Whisper: CPU (ctranslate2 incompatible with MPS), Pyannote: MPS (GPU-accelerated)"
3. If CUDA detected: Use GPU for both whisperx and pyannote; verify compute capability ≥ 3.0
4. If AMD ROCm: Use `ROCM_HOME` env var; test with `torch.cuda.is_available()` after ROCm setup
5. If CPU only: Warn user of slow runtime (4–10x slower than GPU)

### Out of Memory (OOM) During Transcription

**Symptom:** Process killed or `RuntimeError: CUDA out of memory` or `MemoryError: Unable to allocate...`

**Handling:**
1. **For CUDA OOM:** Try smaller model (base → tiny). Reduce batch size (--chunk_size 5 instead of 30). Run inference on CPU as fallback.
2. **For system RAM OOM:** Close other applications. Reduce batch size. Use tiny model.
3. **Retry with degraded model:** Log warning, update checkpoint, continue. User warned in quality_notes.
4. **If still OOM:** Suggest audio segmentation: split into 30min chunks, transcribe separately, manual merge.
5. Do not silently fail — report exact memory used vs available.

### Out of Memory During Alignment

**Symptom:** ctranslate2 allocation failure during word-level timestamp generation.

**Handling:**
1. **Fallback to segment-level timestamps** — Skip alignment, use segment boundaries only. Quality degrades to medium.
2. Log: "Alignment OOM; reverted to segment-level timestamps."
3. Quality note: "Speaker boundaries are approximate; word-level timing unavailable."
4. Continue to diarization.

### Diarization Speaker Count Mismatch

**Symptom:** Pyannote detects N speakers, but transcript has M distinct speaker segments (M ≠ N). Or pyannote assigns SPEAKER_99 but transcript only has SPEAKER_00–SPEAKER_05.

**Handling:**
1. **Background noise as speaker:** Pyannote may detect non-speech noise as separate "speaker". Filter out very short diarization segments (< 3 sec). If removed, re-cluster.
2. **Over-segmentation:** Pyannote may split one speaker into multiple labels due to voice variation. Check if speaker_map can merge them (e.g., SPEAKER_00 and SPEAKER_01 are same person). Prompt user for verification if uncertain.
3. **Under-segmentation:** Pyannote may merge two speakers. Check timestamp boundaries; if unclear, flag as [POTENTIAL_SPEAKER_BOUNDARY] in output for manual review.
4. Log mismatch; do not silently choose one. Include in quality_notes.

## Checkpointing & Resumption

P2 is designed for **checkpoint-based resumption**. Each stage writes a JSON file to `.mdpowers/cache/{content_id}/`:

**Checkpoint files:**
- **01_transcription.json** — Whisper segments, text, timestamps, confidence
- **02_alignment.json** — Word-level timestamps, phoneme-level if available
- **03_diarization.json** — Speaker labels, segment boundaries
- **04_merged.json** — Transcript + diarization combined
- **05_speaker_map.json** — SPEAKER_XX → names mapping

**Checkpoint lifecycle:**
- Created when stage completes successfully
- **7-day expiry:** If > 7 days old, warn user ("Cache is 10 days old; re-run diarization?")
- **Resume on re-invoke:** If user re-runs with same source, check for existing checkpoints. Skip to first missing stage.
- **Override:** `--force` flag skips checkpoints, re-runs from scratch.

**Cache size:** Typically 500MB–2GB per long-form content (model cache separate). Advise user to manage manually or auto-cleanup after 30 days.

## Runner Reference

**Script:** `scripts/whisperx_local.py`

**Usage:**
```bash
python scripts/whisperx_local.py \
  --input "path/to/audio.mp3" \
  --output transcripts/my_transcript.md \
  --model base \
  --device cuda \
  --vocab-overlay vocabularies/my_domain.json \
  --speakers "Alice,Bob"
```

**Key parameters:**
- `--input`: Local audio/video file path or YouTube URL (required)
- `--output`: Output markdown path (optional; default: `{cwd}/transcripts/{auto_named}.md`)
- `--model`: Whisper model size (tiny, base, small, medium, large; default: base)
- `--device`: cuda | mps | cpu (default: auto-detect; **force cpu if mps detected**)
- `--language`: ISO 639-1 code (en, es, fr, etc.; default: auto-detect)
- `--vocab-overlay`: Path to JSON overlay vocabulary file (optional)
- `--speakers`: Comma-separated speaker names or "auto" for LLM guess (default: auto)
- `--force`: Re-run from scratch, ignore checkpoints (optional boolean)
- `--diarization-model`: pyannote model version (default: 3.1)
- `--keep-cache`: Preserve cache after completion (default: true); set false to delete

**Exit codes:**
- 0: Success
- 1: Invalid input file
- 2: Missing dependencies
- 3: HF_TOKEN invalid or missing
- 4: Transcription failed
- 5: OOM (retry with smaller model)
- 6: GPU/device error

**Typical runtime:**
- 5 min audio, base model, GPU: 2–5 min
- 30 min audio, base model, GPU: 15–30 min
- 1 hour audio, large model, CPU: 60+ min
