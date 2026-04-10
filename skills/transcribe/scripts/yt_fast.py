#!/usr/bin/env python3
"""
Path 1 runner — fast YouTube transcription with native subs and Whisper API fallback.

Fetches YouTube native subtitles (manual → auto → Whisper API fallback),
applies vocabulary correction, generates summary, runs vocab candidate discovery,
and builds Path 1-shaped markdown output.
"""

import sys
import argparse
import logging
from pathlib import Path
from typing import Optional, Union
from datetime import datetime, timezone
import json
import subprocess
import tempfile

# Add lib/ to path for relative imports
sys.path.insert(0, str(Path(__file__).parent))

from lib import ytdlp_helpers, vocabulary, llm_review, markdown_builder, errors

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os

# Constants
MAX_BYTES = 24 * 1024 * 1024   # 24 MB — stay under OpenAI's 25 MB limit
CHUNK_MINUTES = 10              # chunk duration when splitting for Whisper API

logger = logging.getLogger(__name__)


def _get_duration(path: Path) -> float:
    """
    Get audio duration in seconds using ffprobe.

    Args:
        path: Path to audio file

    Returns:
        Duration in seconds

    Raises:
        RuntimeError: If ffprobe fails
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1:nokey=1",
                str(path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        raise RuntimeError(f"Failed to get duration for {path}: {e}")


def _split_audio(path: Path, tmpdir: Path, chunk_seconds: int) -> list[tuple[float, Path]]:
    """
    Split audio file into chunks using ffmpeg.

    Args:
        path: Path to audio file
        tmpdir: Temporary directory for chunks
        chunk_seconds: Duration of each chunk in seconds

    Returns:
        List of (start_time, chunk_path) tuples

    Raises:
        RuntimeError: If ffmpeg fails
    """
    tmpdir.mkdir(parents=True, exist_ok=True)
    chunks = []

    try:
        duration = _get_duration(path)
    except RuntimeError:
        raise

    num_chunks = int(duration / chunk_seconds) + (1 if duration % chunk_seconds > 0 else 0)

    for i in range(num_chunks):
        start_time = i * chunk_seconds
        output_path = tmpdir / f"chunk_{i:04d}.mp3"

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(path),
                    "-ss", str(start_time),
                    "-t", str(chunk_seconds),
                    "-c:a", "libmp3lame",
                    "-b:a", "128k",
                    "-y",
                    str(output_path)
                ],
                capture_output=True,
                check=True
            )
            chunks.append((start_time, output_path))
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to split audio chunk {i}: {e}")

    return chunks


def _call_whisper(client, audio_path: Path, prompt: str = "") -> list[dict]:
    """
    Call OpenAI Whisper API for a single audio file.

    Args:
        client: OpenAI client instance
        audio_path: Path to audio file
        prompt: Optional prompt for context

    Returns:
        List of segment dicts with text, start, end fields

    Raises:
        RuntimeError: If API call fails
    """
    try:
        with open(audio_path, "rb") as f:
            response = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
                prompt=prompt if prompt else None
            )

        # Extract segments from verbose JSON response
        if hasattr(response, "segments"):
            return response.segments
        elif isinstance(response, dict) and "segments" in response:
            return response["segments"]
        else:
            # Fallback: wrap full text as single segment
            text = response.text if hasattr(response, "text") else str(response)
            return [{"text": text, "start": 0.0, "end": 0.0}]

    except Exception as e:
        raise RuntimeError(f"Whisper API call failed for {audio_path}: {e}")


def _transcribe_with_chunks(client, mp3_path: Path, prompt: str = "") -> list[dict]:
    """
    Transcribe audio file using Whisper API, splitting if necessary for files >24MB.

    Args:
        client: OpenAI client instance
        mp3_path: Path to MP3 file
        prompt: Optional prompt for context

    Returns:
        List of segment dicts with text, start, end fields

    Raises:
        RuntimeError: If transcription fails
    """
    file_size = mp3_path.stat().st_size

    # If file is under limit, transcribe directly
    if file_size <= MAX_BYTES:
        return _call_whisper(client, mp3_path, prompt)

    # Otherwise split and transcribe chunks
    logger.info(f"File {file_size / 1024 / 1024:.1f} MB exceeds limit, splitting...")
    chunk_seconds = CHUNK_MINUTES * 60

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        chunks = _split_audio(mp3_path, tmpdir_path, chunk_seconds)

        all_segments = []
        for start_time, chunk_path in chunks:
            logger.info(f"Transcribing chunk starting at {start_time}s...")
            chunk_segments = _call_whisper(client, chunk_path, prompt)

            # Adjust timestamps to account for chunk offset
            for segment in chunk_segments:
                if isinstance(segment, dict):
                    if "start" in segment:
                        segment["start"] = segment.get("start", 0) + start_time
                    if "end" in segment:
                        segment["end"] = segment.get("end", 0) + start_time

            all_segments.extend(chunk_segments)

        return all_segments


def run(
    source: str,
    out_dir: Path,
    vocab_overlay: Optional[Path] = None,
    skip_vocab_review: bool = False,
    openai_client=None,
    cookies_file=None,
    cookies_browser=None
) -> Path:
    """
    Main Path 1 runner: fetch video, transcribe, correct vocab, build markdown.

    Args:
        source: YouTube URL
        out_dir: Output directory for markdown file
        vocab_overlay: Optional path to vocabulary overlay JSON
        skip_vocab_review: Skip vocab review step if True
        openai_client: OpenAI client instance (created if None)
        cookies_file: Path to cookies file for yt-dlp
        cookies_browser: Browser name to extract cookies from for yt-dlp

    Returns:
        Path to generated markdown file

    Raises:
        errors.TranscriptError: If transcription fails
        errors.VocabularyError: If vocabulary operations fail
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Get video metadata
    logger.info(f"Fetching metadata for {source}...")
    try:
        info = ytdlp_helpers.get_video_info(
            source,
            cookies_file=cookies_file,
            cookies_browser=cookies_browser
        )
    except Exception as e:
        raise errors.TranscriptError(f"Failed to get video info: {e}")

    video_id = info.get("id", "unknown")
    title = info.get("title", "Untitled")
    channel = info.get("uploader", "Unknown Channel")
    raw_date = info.get("upload_date", "")
    published = _format_date(raw_date)
    duration_sec = info.get("duration", 0)
    duration_formatted = _format_duration(duration_sec)

    # Step 2: Try native subtitles first (manual → auto)
    logger.info("Attempting to fetch native YouTube subtitles...")
    subtitles = ytdlp_helpers.fetch_subtitles(source, cookies_file=cookies_file, cookies_browser=cookies_browser)

    transcript_method = None
    quality = "full"
    quality_notes = ""
    segments = []

    if subtitles:
        segments = subtitles
        if len(subtitles) > 0 and "manual" in str(subtitles[0].get("source", "")):
            transcript_method = "youtube-manual-subs"
        else:
            transcript_method = "youtube-auto-captions"
        logger.info(f"Using {transcript_method}")
    else:
        # Step 3: Fallback to Whisper API
        logger.info("No native subs found, falling back to Whisper API...")
        quality = "degraded"
        quality_notes = "Generated via Whisper API (no human review)"
        transcript_method = "whisper-api-fallback-no-diarization"

        # Download audio
        try:
            audio_path = ytdlp_helpers.download_audio(
                source,
                out_dir=out_dir,
                cookies_file=cookies_file,
                cookies_browser=cookies_browser
            )
        except Exception as e:
            raise errors.TranscriptError(f"Failed to download audio: {e}")

        # Create OpenAI client if not provided
        if openai_client is None:
            try:
                from openai import OpenAI
                openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            except Exception as e:
                raise errors.TranscriptError(f"Failed to create OpenAI client: {e}")

        # Transcribe with chunking if needed
        try:
            raw_segments = _transcribe_with_chunks(openai_client, audio_path)
            segments = raw_segments
        except Exception as e:
            raise errors.TranscriptError(f"Whisper transcription failed: {e}")

        # Clean up audio file
        try:
            audio_path.unlink()
        except Exception:
            pass

    # Step 4: Load vocabulary and apply correction
    logger.info("Loading vocabulary and applying corrections...")
    try:
        vocab = vocabulary.load_vocabulary(overlay_path=vocab_overlay)
        for segment in segments:
            if isinstance(segment, dict) and "text" in segment:
                segment["text"] = vocabulary.apply_vocabulary(segment["text"], vocab)
    except errors.VocabularyError as e:
        logger.warning(f"Vocabulary loading failed: {e}")
        vocab = {}

    # Step 5: Generate summary
    logger.info("Generating summary...")
    try:
        transcript_text = " ".join([
            seg.get("text", "") if isinstance(seg, dict) else str(seg)
            for seg in segments
        ])
        summary = llm_review.generate_summary(transcript_text)
    except Exception as e:
        logger.warning(f"Summary generation failed: {e}")
        summary = ""

    # Step 6: Vocab review (unless skipped)
    vocab_review = None
    if not skip_vocab_review:
        logger.info("Running vocabulary candidate discovery...")
        try:
            candidates = vocabulary.find_vocabulary_candidates(transcript_text, vocab)
            assessed = vocabulary.gpt_assess_candidates(candidates)
            vocab_review = vocabulary.write_vocabulary_review(assessed)
        except Exception as e:
            logger.warning(f"Vocab review failed: {e}")

    # Step 7: Build frontmatter
    logger.info("Building markdown output...")
    frontmatter = {
        "title": title,
        "source": source,
        "channel": channel,
        "published": published,
        "duration": duration_formatted,
        "transcript_method": transcript_method,
        "pathway": "P1",
        "quality": quality,
        "quality_notes": quality_notes,
        "vocab_master_version": vocab.get("_version", "unknown") if vocab else "unknown",
        "vocab_overlay": str(vocab_overlay) if vocab_overlay else None,
        "transcribed_at": datetime.now(timezone.utc).isoformat()
    }

    # Step 8: Build markdown
    markdown_text = markdown_builder.build_path1_markdown(
        frontmatter=frontmatter,
        segments=segments,
        summary=summary,
        vocab_review=vocab_review
    )

    # Step 9: Resolve output path and handle conflicts
    output_path = markdown_builder.resolve_output_path(
        out_dir=out_dir,
        title=title,
        video_id=video_id
    )

    output_path = markdown_builder.handle_overwrite_conflict(output_path)

    # Step 10: Write file
    logger.info(f"Writing output to {output_path}...")
    try:
        output_path.write_text(markdown_text, encoding="utf-8")
    except Exception as e:
        raise errors.TranscriptError(f"Failed to write output file: {e}")

    logger.info(f"Done! Output: {output_path}")
    return output_path


def _format_date(raw_date: str) -> str:
    """
    Format upload date from YYYYMMDD format to YYYY-MM-DD.

    Args:
        raw_date: Date string in YYYYMMDD format

    Returns:
        Date string in YYYY-MM-DD format, or empty string if invalid
    """
    if not raw_date or len(raw_date) != 8:
        return ""
    try:
        return f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    except Exception:
        return ""


def _format_duration(seconds: int) -> str:
    """
    Format duration in seconds to HH:MM:SS.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string
    """
    if not seconds:
        return "00:00:00"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main():
    """Parse CLI arguments and run transcription."""
    parser = argparse.ArgumentParser(
        description="Path 1 runner: fast YouTube transcription with native subs and Whisper API fallback"
    )
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path.cwd(),
        help="Output directory (default: current directory)"
    )
    parser.add_argument(
        "--vocab-overlay",
        type=Path,
        help="Path to vocabulary overlay JSON"
    )
    parser.add_argument(
        "--skip-vocab-review",
        action="store_true",
        help="Skip vocabulary review step"
    )
    parser.add_argument(
        "--cookies-file",
        type=Path,
        help="Path to cookies file for yt-dlp"
    )
    parser.add_argument(
        "--cookies-from-browser",
        type=str,
        help="Browser name to extract cookies from (chrome, firefox, safari, etc.)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s — %(name)s — %(levelname)s — %(message)s"
    )

    try:
        output_path = run(
            source=args.url,
            out_dir=args.out,
            vocab_overlay=args.vocab_overlay,
            skip_vocab_review=args.skip_vocab_review,
            cookies_file=args.cookies_file,
            cookies_browser=args.cookies_from_browser
        )
        print(f"✓ Transcription complete: {output_path}")
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=args.verbose)
        sys.exit(1)


if __name__ == "__main__":
    main()
