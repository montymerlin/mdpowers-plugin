#!/usr/bin/env python3
"""
WhisperX Local Pipeline Runner (Path 2)

Heavy transcription pipeline with diarization, speaker identification, and checkpointing.
Orchestrates: WhisperX (audio→transcript+alignment), pyannote (diarization),
speaker mapping, vocabulary correction, LLM quirks review, and markdown output.

Port of diarize.py process() orchestrator. Includes PyTorch 2.6+ compatibility,
device handling (CPU for WhisperX ctranslate2, MPS/GPU for pyannote), and OOM fallback.
"""

import argparse
import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# PyTorch 2.6+ compatibility patch — must come before any torch/whisperx imports
#
# PyTorch 2.6 changed torch.load's default from weights_only=False to weights_only=True.
# Older pyannote/omegaconf checkpoints include ListConfig/DictConfig objects which are
# not in the default safe-globals allowlist, causing UnpicklingError at model load time.
#
# Two patches are required:
#   1. Add omegaconf types to torch's safe_globals allowlist
#   2. Patch lightning_fabric's _load helper to force weights_only=False (belt-and-suspenders)
#
# Both patches must be applied before any whisperx/pyannote import.
# Discovered during EthicHub podcast transcription pass, April 2026.
try:
    import torch as _torch_compat

    # Patch 1: allow omegaconf types in safe globals (PyTorch 2.6+)
    try:
        import omegaconf.listconfig as _olc
        import omegaconf.dictconfig as _odc
        _torch_compat.serialization.add_safe_globals([
            _olc.ListConfig,
            _odc.DictConfig,
        ])
    except Exception:
        pass

    # Patch 2: force weights_only=False in lightning_fabric's checkpoint loader
    from lightning_fabric.utilities import cloud_io as _lf_io

    def _patched_lf_load(path_or_url, map_location=None, **kwargs):
        """Patch lightning_fabric's _load to disable weights_only check for older checkpoints."""
        kwargs["weights_only"] = False
        return _torch_compat.load(path_or_url, map_location=map_location, **kwargs)

    _lf_io._load = _patched_lf_load
except Exception:
    pass

# Add lib to path for local imports
sys.path.insert(0, str(Path(__file__).parent))

from lib import (
    diarization_cleanup,
    errors,
    host_mode,
    llm_review,
    markdown_builder,
    speakers,
    vocabulary,
    ytdlp_helpers,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Checkpoint Helpers
# ============================================================================


def _cache_dir(workspace_root: Path, video_id: str) -> Path:
    """
    Get checkpoint cache directory for a video.

    Args:
        workspace_root: Root path of the mdpowers workspace
        video_id: Video identifier (YouTube ID, URL slug, etc.)

    Returns:
        Path to cache directory (.mdpowers/cache/{video_id}/)
    """
    return workspace_root / ".mdpowers" / "cache" / video_id


def _save_checkpoint(cache_dir: Path, name: str, data) -> None:
    """
    Save a checkpoint to cache directory.

    JSON serializable dicts/lists are written as JSON.
    Strings are written as plain text files.

    Args:
        cache_dir: Directory to save checkpoint in
        name: Checkpoint name (becomes filename without extension)
        data: Data to save (dict, list, or str)
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    filepath = cache_dir / f"{name}.json" if isinstance(data, (dict, list)) else cache_dir / f"{name}.txt"

    if isinstance(data, str):
        filepath.write_text(data, encoding="utf-8")
    else:
        filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info(f"Saved checkpoint: {filepath}")


def _load_checkpoint(cache_dir: Path, name: str):
    """
    Load a checkpoint from cache directory.

    Returns dict/list from .json or string from .txt.

    Args:
        cache_dir: Directory to load checkpoint from
        name: Checkpoint name

    Returns:
        Loaded data (dict, list, or str), or None if not found
    """
    for suffix in [".json", ".txt"]:
        filepath = cache_dir / f"{name}{suffix}"
        if filepath.exists():
            if suffix == ".json":
                return json.loads(filepath.read_text(encoding="utf-8"))
            else:
                return filepath.read_text(encoding="utf-8")
    return None


def _checkpoint_exists(cache_dir: Path, name: str) -> bool:
    """
    Check if a checkpoint exists in cache directory.

    Args:
        cache_dir: Directory to check
        name: Checkpoint name

    Returns:
        True if checkpoint exists (either .json or .txt)
    """
    return (cache_dir / f"{name}.json").exists() or (cache_dir / f"{name}.txt").exists()


# ============================================================================
# WhisperX Pipeline
# ============================================================================


def _run_whisperx_transcribe(audio_path: Path, prompt: str = "") -> dict:
    """
    Run WhisperX transcription with word-level alignment.

    Loads large-v2 model on CPU (ctranslate2 does not support MPS).
    Performs word-level alignment with OOM fallback to medium model.

    Args:
        audio_path: Path to audio file
        prompt: Optional initial prompt for Whisper context

    Returns:
        WhisperX result dict with segments, language, etc.

    Raises:
        RuntimeError: If transcription fails after fallback attempts
    """
    import whisperx

    logger.info(f"Loading WhisperX model (large-v2, CPU)...")
    device = "cpu"  # ctranslate2 does not support MPS; force CPU even on Apple Silicon

    try:
        model = whisperx.load_model(
            "large-v2",
            device=device,
            compute_type="int8",
            asr_options={"initial_prompt": prompt} if prompt else {},
        )

        logger.info(f"Transcribing audio: {audio_path}")
        audio = whisperx.load_audio(str(audio_path))
        result = model.transcribe(audio, batch_size=8, language=None)

        logger.info("Aligning segments with word-level timestamps...")
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

        return result

    except (MemoryError, RuntimeError) as e:
        if "CUDA out of memory" in str(e) or "memory" in str(e).lower():
            logger.warning(f"OOM on large-v2, retrying with medium model...")
            # Clear model and retry
            import gc

            gc.collect()
            model = whisperx.load_model(
                "medium",
                device=device,
                compute_type="int8",
                asr_options={"initial_prompt": prompt} if prompt else {},
            )
            audio = whisperx.load_audio(str(audio_path))
            result = model.transcribe(audio, batch_size=8, language=None)
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)
            return result
        else:
            raise


def _run_diarization(audio_path: Path, hf_token: str, num_speakers: Optional[int] = None) -> dict:
    """
    Run pyannote diarization on audio.

    Pyannote CAN use MPS/GPU; device selection handled internally.

    Args:
        audio_path: Path to audio file
        hf_token: Hugging Face token for model access
        num_speakers: Optional num_speakers hint; None = auto-detect

    Returns:
        Diarization result dict (pyannote Diarization object)
    """
    from pyannote.audio import Pipeline

    logger.info("Loading pyannote diarization pipeline...")
    pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=hf_token)

    logger.info(f"Running diarization: {audio_path}")
    diarization = pipeline(str(audio_path), num_speakers=num_speakers)

    return diarization


def _assign_speakers(result: dict, diarization) -> list:
    """
    Assign speakers to word-level segments using pyannote diarization result.

    Normalizes SPEAKER_0, SPEAKER_1, etc. to SPEAKER_00, SPEAKER_01 via regex.

    Args:
        result: WhisperX transcription result dict with segments
        diarization: pyannote Diarization object

    Returns:
        List of segments with speaker assignments added
    """
    import re

    import whisperx

    logger.info("Assigning speakers to words...")
    segments = whisperx.diarize.assign_word_speakers(result["segments"], diarization)

    # Normalize SPEAKER_0 → SPEAKER_00, SPEAKER_1 → SPEAKER_01, etc.
    for segment in segments:
        for word in segment.get("words", []):
            if "speaker" in word:
                speaker = word["speaker"]
                # Convert SPEAKER_N to SPEAKER_0N (zero-padded)
                word["speaker"] = re.sub(r"SPEAKER_(\d)$", r"SPEAKER_0\1", speaker)

    return segments


# ============================================================================
# Main Runner
# ============================================================================


def run(
    source: str,
    out_dir: Path,
    hf_token: str,
    openai_client=None,
    vocab_overlay: Optional[Path] = None,
    skip_vocab_review: bool = False,
    known_speakers: Optional[list[str]] = None,
    num_speakers: Optional[int] = None,
    cookies_file: Optional[str] = None,
    cookies_browser: Optional[str] = None,
    auto: bool = True,
) -> Path:
    """
    Run full WhisperX Path 2 pipeline: download, transcribe, diarize, identify speakers, correct, review, output.

    Pipeline steps (with checkpointing):
    1. Get video metadata, setup cache
    2. Download audio (skip if cached)
    3. Load vocabulary and build Whisper initial_prompt
    4. Run WhisperX transcription + alignment (checkpoint: raw_transcript)
    5. Run pyannote diarization (checkpoint: diarization)
    6. Assign speakers to words (checkpoint: assigned)
    7. Apply vocabulary post-correction
    8. Merge short speaker blocks
    9. Speaker identification (known or research-based)
    10. Apply speaker mapping to segments
    11. LLM quirks review + autocorrection
    12. Generate summary
    13. Optional: discover vocab candidates
    14. Build frontmatter (title, source, pathway=P2, quality=full, etc.)
    15. Build and write markdown output

    Args:
        source: URL or file path to transcribe
        out_dir: Output directory for markdown file
        hf_token: Hugging Face token (for pyannote access)
        openai_client: Optional OpenAI client for LLM operations (if None, skips LLM steps)
        vocab_overlay: Optional path to vocabulary override file
        skip_vocab_review: If True, skip LLM vocab candidate discovery
        known_speakers: Optional list of speaker names in order (e.g., ["Alice", "Bob"])
        num_speakers: Optional hint for speaker count
        cookies_file: Optional path to cookies file for yt-dlp
        cookies_browser: Optional browser name to extract cookies from (e.g., "firefox")
        auto: If True, auto-confirm overwrite prompts (for batch mode)

    Returns:
        Path to generated markdown file

    Raises:
        errors.TranscriptionError: On fatal pipeline errors
    """
    workspace_root = Path.cwd()
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Path 2 Pipeline starting: {source}")

    try:
        # Step 1: Get video metadata and cache directory
        logger.info("Step 1: Fetching video metadata...")
        metadata = ytdlp_helpers.get_video_metadata(source, cookies_file=cookies_file, cookies_browser=cookies_browser)
        video_id = metadata["id"]
        cache_dir = _cache_dir(workspace_root, video_id)
        cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Video ID: {video_id}")
        logger.info(f"Title: {metadata.get('title', 'Unknown')}")
        logger.info(f"Cache: {cache_dir}")

        # Step 2: Download audio (skip if cached)
        logger.info("Step 2: Downloading audio...")
        audio_path = cache_dir / "audio.m4a"
        if audio_path.exists():
            logger.info(f"Audio already cached: {audio_path}")
        else:
            audio_path = ytdlp_helpers.download_audio(
                source, cache_dir, cookies_file=cookies_file, cookies_browser=cookies_browser
            )

        # Step 3: Load vocabulary and build Whisper prompt
        logger.info("Step 3: Building Whisper initial prompt...")
        vocab_config = vocabulary.load_vocabulary(vocab_overlay)
        whisper_prompt = vocabulary.build_whisper_prompt(vocab_config)

        # Step 4: Run WhisperX transcription + alignment
        logger.info("Step 4: WhisperX transcription + alignment...")
        if _checkpoint_exists(cache_dir, "raw_transcript"):
            logger.info("Loading cached raw transcript...")
            raw_result = _load_checkpoint(cache_dir, "raw_transcript")
        else:
            raw_result = _run_whisperx_transcribe(audio_path, prompt=whisper_prompt)
            _save_checkpoint(cache_dir, "raw_transcript", raw_result)

        # Step 5: Run pyannote diarization
        logger.info("Step 5: Pyannote diarization...")
        if _checkpoint_exists(cache_dir, "diarization"):
            logger.info("Loading cached diarization...")
            diarization = _load_checkpoint(cache_dir, "diarization")
        else:
            diarization = _run_diarization(audio_path, hf_token, num_speakers=num_speakers)
            _save_checkpoint(cache_dir, "diarization", str(diarization))

        # Step 6: Assign speakers to words
        logger.info("Step 6: Assigning speakers to word-level segments...")
        if _checkpoint_exists(cache_dir, "assigned"):
            logger.info("Loading cached speaker assignments...")
            segments = _load_checkpoint(cache_dir, "assigned")
        else:
            segments = _assign_speakers(raw_result, diarization)
            _save_checkpoint(cache_dir, "assigned", segments)

        # Step 7: Apply vocabulary post-correction
        logger.info("Step 7: Applying vocabulary corrections...")
        segments = vocabulary.apply_vocabulary(segments, vocab_config)

        # Step 8: Merge short speaker blocks
        logger.info("Step 8: Merging short speaker blocks...")
        segments = diarization_cleanup.merge_short_speaker_blocks(segments)

        # Step 9: Speaker identification
        logger.info("Step 9: Speaker identification...")
        if known_speakers:
            logger.info(f"Using provided speaker list: {known_speakers}")
            speaker_mapping = speakers.map_speakers_by_order(segments, known_speakers)
        else:
            logger.info("Researching speakers from metadata...")
            speaker_info = speakers.research_speakers_from_metadata(metadata)
            if not speaker_info or len(speaker_info) < len(set(seg.get("speaker") for seg in segments)):
                logger.info("Insufficient metadata; inferring speakers from audio patterns...")
                speaker_info = speakers.guess_speakers(segments)
            speaker_mapping = speaker_info

        # Step 10: Apply speaker mapping
        logger.info("Step 10: Applying speaker mapping to segments...")
        for segment in segments:
            speaker = segment.get("speaker")
            if speaker and speaker in speaker_mapping:
                segment["speaker"] = speaker_mapping[speaker]

        # Step 11: LLM quirks review + autocorrection
        if openai_client:
            logger.info("Step 11: LLM quirks review...")
            quirks = llm_review.llm_quirks_review(segments, openai_client)
            segments = llm_review.apply_llm_quirk_autocorrections(segments, quirks)
        else:
            logger.info("Step 11: Skipping LLM quirks review (no OpenAI client)")

        # Step 12: Generate summary
        if openai_client:
            logger.info("Step 12: Generating summary...")
            summary = llm_review.generate_summary(segments, openai_client)
        else:
            logger.info("Step 12: Skipping summary generation (no OpenAI client)")
            summary = None

        # Step 13: Vocab candidate discovery (optional)
        vocab_candidates = []
        if not skip_vocab_review and openai_client:
            logger.info("Step 13: Discovering vocabulary candidates...")
            vocab_candidates = llm_review.discover_vocab_candidates(segments, openai_client)

        # Step 14: Build frontmatter
        logger.info("Step 14: Building frontmatter...")
        host_info = host_mode.infer_host_cohost_guests(segments)

        frontmatter = {
            "title": metadata.get("title", "Untitled"),
            "source": source,
            "channel": metadata.get("channel", "Unknown"),
            "published": metadata.get("upload_date", ""),
            "duration": metadata.get("duration", 0),
            "transcript_method": "whisperx-local",
            "pathway": "P2",
            "quality": "full",
            "host": host_info.get("host"),
            "co_host": host_info.get("co_host"),
            "guests": host_info.get("guests"),
            "vocab_master_version": vocab_config.get("version", "unknown"),
            "transcribed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Step 15: Build and write markdown
        logger.info("Step 15: Building markdown output...")
        markdown_content = markdown_builder.build_path2_markdown(
            frontmatter=frontmatter,
            segments=segments,
            summary=summary,
            vocab_candidates=vocab_candidates,
        )

        # Resolve output filename and write
        out_filename = f"{video_id}.md"
        out_path = out_dir / out_filename

        if out_path.exists() and not auto:
            response = input(f"\n{out_path} already exists. Overwrite? [y/N]: ").strip().lower()
            if response != "y":
                logger.info("Cancelled.")
                return out_path

        logger.info(f"Writing output: {out_path}")
        out_path.write_text(markdown_content, encoding="utf-8")

        logger.info(f"✓ Path 2 complete: {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        logger.error(traceback.format_exc())
        raise errors.TranscriptionError(f"Path 2 pipeline failed: {e}") from e


# ============================================================================
# CLI
# ============================================================================


def main():
    """
    Command-line interface for WhisperX local pipeline.

    Usage:
        python whisperx_local.py "https://www.youtube.com/watch?v=..." \
            --out /path/to/output \
            --hf-token YOUR_HF_TOKEN \
            --speakers Alice Bob
    """
    parser = argparse.ArgumentParser(
        description="WhisperX local transcription pipeline (Path 2) with diarization and speaker ID"
    )

    parser.add_argument("source", help="URL or file path to transcribe")
    parser.add_argument("--out", "-o", type=Path, required=True, help="Output directory for markdown")
    parser.add_argument("--hf-token", required=True, help="Hugging Face token (for pyannote)")
    parser.add_argument("--vocab-overlay", type=Path, help="Optional vocabulary override file")
    parser.add_argument("--skip-vocab-review", action="store_true", help="Skip LLM vocab candidate discovery")
    parser.add_argument("--speakers", nargs="+", help="Known speaker names in order (e.g., Alice Bob)")
    parser.add_argument("--num-speakers", type=int, help="Hint for number of speakers")
    parser.add_argument("--cookies-file", help="Path to yt-dlp cookies file")
    parser.add_argument("--cookies-from-browser", help="Extract cookies from browser (e.g., firefox)")
    parser.add_argument("--auto", action="store_true", help="Auto-confirm overwrite prompts")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        # Run pipeline
        output_path = run(
            source=args.source,
            out_dir=args.out,
            hf_token=args.hf_token,
            vocab_overlay=args.vocab_overlay,
            skip_vocab_review=args.skip_vocab_review,
            known_speakers=args.speakers,
            num_speakers=args.num_speakers,
            cookies_file=args.cookies_file,
            cookies_browser=args.cookies_from_browser,
            auto=args.auto,
        )
        print(f"\n✓ Output: {output_path}")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
