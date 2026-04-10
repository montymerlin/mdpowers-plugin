"""YouTube and yt-dlp operations helper module.

This module consolidates all yt-dlp-related operations:
- Cookie handling (no cookies, file-based, browser-based fallback)
- Video metadata fetching via --dump-json
- Subtitle downloading (manual subs, auto-captions, json3 format)
- JSON3 parsing (yt-dlp subtitle format)
- Audio downloading
- Filename sanitization
- Duration probing via ffprobe

Functions handle cookie fallback chains transparently, raising ProbeError
on failures. JSON3 parsing converts yt-dlp subtitle format to normalized
{start, end, text} segments.
"""

import json
import re
import subprocess
from pathlib import Path
from typing import Optional

from .errors import ProbeError, TranscribeError


# ---------------------------------------------------------------------------
# Auth error detection
# ---------------------------------------------------------------------------

_AUTH_ERROR_PATTERNS = (
    "Sign in to confirm",
    "bot detection",
    "This video is only available",
    "Private video",
    "members-only",
    "age-restricted",
    "This video requires",
)


def _is_auth_error(stderr: str) -> bool:
    """Check if stderr indicates an authentication or access error.

    Args:
        stderr: The stderr output from yt-dlp.

    Returns:
        True if stderr matches known auth error patterns.
    """
    return any(pattern in stderr for pattern in _AUTH_ERROR_PATTERNS)


# ---------------------------------------------------------------------------
# Core yt-dlp subprocess wrapper
# ---------------------------------------------------------------------------


def _yt_run(cmd_args, cookies_file=None, cookies_browser=None):
    """Run yt-dlp subprocess with cookie fallback chain.

    Attempts execution in this order:
    1. No cookies (for public content)
    2. Cookies file (if provided and file exists)
    3. Browser cookies (if provided)

    Args:
        cmd_args: List of yt-dlp arguments (without 'yt-dlp' prefix).
        cookies_file: Optional path to cookies.txt file.
        cookies_browser: Optional browser name (e.g., 'firefox', 'chrome').

    Returns:
        CompletedProcess with stdout and stderr.

    Raises:
        ProbeError: If all attempts fail.
    """
    # Attempt 1: No cookies
    cmd = ["yt-dlp"] + cmd_args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return result
    if not _is_auth_error(result.stderr):
        raise ProbeError(f"yt-dlp failed: {result.stderr}")

    # Attempt 2: Cookies file
    if cookies_file and Path(cookies_file).is_file():
        cmd = ["yt-dlp", "--cookies", str(cookies_file)] + cmd_args
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result
        if not _is_auth_error(result.stderr):
            raise ProbeError(f"yt-dlp with cookies file failed: {result.stderr}")

    # Attempt 3: Browser cookies
    if cookies_browser:
        cmd = ["yt-dlp", "--cookies-from-browser", cookies_browser] + cmd_args
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result
        raise ProbeError(f"yt-dlp with browser cookies failed: {result.stderr}")

    # All attempts failed
    raise ProbeError(
        f"yt-dlp could not access video (possibly authentication required). "
        f"Try providing cookies via --cookies-file or --cookies-browser."
    )


# ---------------------------------------------------------------------------
# Video metadata fetching
# ---------------------------------------------------------------------------


def get_video_info(url, cookies_file=None, cookies_browser=None) -> dict:
    """Fetch video metadata from URL via yt-dlp --dump-json.

    Args:
        url: YouTube URL.
        cookies_file: Optional path to cookies.txt file.
        cookies_browser: Optional browser name for cookie extraction.

    Returns:
        Parsed JSON dict with video metadata (title, duration, etc.).

    Raises:
        ProbeError: If yt-dlp fails.
    """
    result = _yt_run(
        ["--dump-json", url],
        cookies_file=cookies_file,
        cookies_browser=cookies_browser,
    )
    if result.returncode != 0:
        raise ProbeError(f"yt-dlp --dump-json failed: {result.stderr}")
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Subtitle fetching and JSON3 parsing
# ---------------------------------------------------------------------------


def fetch_subtitles(url, tmpdir, cookies_file=None, cookies_browser=None) -> tuple[list[dict], str]:
    """Fetch video subtitles (manual or auto-captions) in json3 format.

    Tries manual subtitles first, falls back to auto-captions if unavailable.
    Returns subtitle segments in normalized {start, end, text} format.

    Args:
        url: YouTube URL.
        tmpdir: Temporary directory for subtitle files.
        cookies_file: Optional path to cookies.txt file.
        cookies_browser: Optional browser name for cookie extraction.

    Returns:
        Tuple of (segments list, method_label string):
        - segments: list of {start, end, text} dicts (times in seconds)
        - method_label: "manual subs" or "auto-captions"

    Raises:
        ProbeError: If subtitle fetching fails or json3 parsing fails.
    """
    tmpdir = Path(tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)

    # Try manual subtitles first
    subtitle_path = tmpdir / "%(title)s.json3"
    result = _yt_run(
        [
            "--write-subs",
            "--sub-langs", "en",
            "-o", str(subtitle_path),
            url,
        ],
        cookies_file=cookies_file,
        cookies_browser=cookies_browser,
    )

    json3_files = list(tmpdir.glob("*.json3"))
    if json3_files and result.returncode == 0:
        segments = parse_json3(json3_files[0])
        return segments, "manual subs"

    # Fall back to auto-captions
    result = _yt_run(
        [
            "--write-auto-subs",
            "--sub-langs", "en",
            "-o", str(subtitle_path),
            url,
        ],
        cookies_file=cookies_file,
        cookies_browser=cookies_browser,
    )

    json3_files = list(tmpdir.glob("*.json3"))
    if json3_files and result.returncode == 0:
        segments = parse_json3(json3_files[0])
        return segments, "auto-captions"

    raise ProbeError(
        f"Could not fetch subtitles for {url}. "
        "Try videos with captions or enable auto-captions."
    )


def parse_json3(path) -> list[dict]:
    """Parse yt-dlp json3 subtitle format to normalized segments.

    Converts yt-dlp's JSON3 format (with ttml:span elements containing
    offset info) to a list of {start, end, text} dicts with times
    in seconds.

    Args:
        path: Path to json3 file.

    Returns:
        List of dicts: [{start: float, end: float, text: str}, ...]

    Raises:
        ProbeError: If file is not valid JSON3 or lacks expected structure.
    """
    path = Path(path)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        raise ProbeError(f"Failed to parse json3 file {path}: {e}")

    segments = []
    try:
        for event in data.get("events", []):
            if event.get("segs") is None:
                continue

            start_ms = event.get("tStartMs")
            dur_ms = event.get("dDurationMs")

            if start_ms is None or dur_ms is None:
                continue

            start_sec = start_ms / 1000.0
            end_sec = (start_ms + dur_ms) / 1000.0

            text_parts = []
            for seg in event["segs"]:
                if isinstance(seg, dict):
                    text_parts.append(seg.get("utf8", ""))
                elif isinstance(seg, str):
                    text_parts.append(seg)

            text = "".join(text_parts).strip()
            if text:
                segments.append(
                    {
                        "start": start_sec,
                        "end": end_sec,
                        "text": text,
                    }
                )
    except (KeyError, TypeError) as e:
        raise ProbeError(f"Invalid json3 structure in {path}: {e}")

    return segments


# ---------------------------------------------------------------------------
# Audio downloading
# ---------------------------------------------------------------------------


def download_audio(url, tmpdir, cookies_file=None, cookies_browser=None) -> Path:
    """Download audio from URL via yt-dlp.

    Saves as best available audio (opus/m4a) with standard naming.

    Args:
        url: YouTube URL.
        tmpdir: Destination directory.
        cookies_file: Optional path to cookies.txt file.
        cookies_browser: Optional browser name for cookie extraction.

    Returns:
        Path to downloaded audio file.

    Raises:
        ProbeError: If download fails.
    """
    tmpdir = Path(tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)

    output_template = str(tmpdir / "%(title)s.%(ext)s")

    result = _yt_run(
        [
            "-f", "bestaudio",
            "-x",
            "--audio-format", "opus",
            "-o", output_template,
            url,
        ],
        cookies_file=cookies_file,
        cookies_browser=cookies_browser,
    )

    if result.returncode != 0:
        raise ProbeError(f"yt-dlp audio download failed: {result.stderr}")

    # Find the downloaded file
    audio_files = list(tmpdir.glob("*"))
    audio_files = [f for f in audio_files if f.suffix in (".opus", ".m4a", ".mp3")]
    if not audio_files:
        raise ProbeError(f"No audio file found in {tmpdir} after download")

    return audio_files[0]


# ---------------------------------------------------------------------------
# Filename sanitization
# ---------------------------------------------------------------------------


def safe_filename(title, max_len=80) -> str:
    """Sanitize a string for use as a filename.

    Removes or replaces problematic characters, truncates to max_len.

    Args:
        title: The input string (e.g., video title).
        max_len: Maximum length of output filename.

    Returns:
        Sanitized filename-safe string.
    """
    # Replace problematic characters
    safe = re.sub(r'[<>:"/\\|?*]', '', title)
    # Collapse multiple spaces/underscores
    safe = re.sub(r'[\s_]+', '_', safe)
    # Remove leading/trailing whitespace and underscores
    safe = safe.strip().strip("_")
    # Truncate
    if len(safe) > max_len:
        safe = safe[:max_len].rstrip("_")
    return safe


# ---------------------------------------------------------------------------
# Duration probing
# ---------------------------------------------------------------------------


def get_duration(path) -> float:
    """Get duration of an audio/video file via ffprobe.

    Args:
        path: Path to audio or video file.

    Returns:
        Duration in seconds (float).

    Raises:
        ProbeError: If ffprobe fails or file has no duration.
    """
    path = Path(path)
    if not path.is_file():
        raise ProbeError(f"File does not exist: {path}")

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1:noprint_wrappers=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise ProbeError("ffprobe not found. Install ffmpeg.")
    except subprocess.TimeoutExpired:
        raise ProbeError(f"ffprobe timeout on {path}")

    if result.returncode != 0:
        raise ProbeError(f"ffprobe failed: {result.stderr}")

    try:
        duration = float(result.stdout.strip())
        return duration
    except (ValueError, IndexError):
        raise ProbeError(f"Could not parse duration from {path}")
