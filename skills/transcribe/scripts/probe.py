#!/usr/bin/env python3
"""Probe script for mdpowers transcribe skill.

Probes a source URL and the environment before routing to a pathway.
Returns a structured ProbeReport with source info, environment capabilities,
and vocabulary state.
"""

import argparse
import importlib.util
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent))

from lib.errors import ProbeError
from lib.host_mode import detect_host_mode, find_workspace_root, get_mdpowers_data_dir
from lib.ytdlp_helpers import get_video_info
from lib.vocabulary import _load_vocab_file


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SourceInfo:
    """Metadata about a single source (YouTube video or local file)."""

    url: str
    title: str
    channel: str
    duration_seconds: float
    duration_formatted: str  # HH:MM:SS
    description: str
    has_manual_subs: bool
    has_auto_captions: bool
    requires_auth: bool
    video_id: str


@dataclass
class EnvProbe:
    """Binary availability of tools and environment variables."""

    yt_dlp: bool
    ffmpeg: bool
    whisperx: bool
    pyannote: bool
    torch: bool
    openai_api_key: bool
    hf_token: bool


@dataclass
class VocabProbe:
    """State of vocabulary files (master + overlays)."""

    master_path: Optional[str]  # None if not found
    master_term_count: int
    overlay_paths: list[str]
    overlay_term_count: int


@dataclass
class ProbeReport:
    """Complete probe results for routing decision."""

    sources: list[SourceInfo]
    env: EnvProbe
    vocab: VocabProbe
    host_mode: str  # "local" or "sandbox"
    workspace_root: str


# ---------------------------------------------------------------------------
# Duration formatting
# ---------------------------------------------------------------------------


def _format_duration(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string like "1:23:45" or "0:05:30".
    """
    total_secs = int(seconds)
    hours = total_secs // 3600
    mins = (total_secs % 3600) // 60
    secs = total_secs % 60
    return f"{hours}:{mins:02d}:{secs:02d}"


# ---------------------------------------------------------------------------
# Source probing
# ---------------------------------------------------------------------------


def probe_youtube(
    url: str, cookies_file: Optional[str] = None, cookies_browser: Optional[str] = None
) -> SourceInfo:
    """Probe a YouTube URL for metadata and subtitle availability.

    Uses yt-dlp to fetch --dump-json, then inspects subtitles and
    automatic_captions dicts for "en" key to determine availability.

    Args:
        url: YouTube URL.
        cookies_file: Optional path to cookies.txt file.
        cookies_browser: Optional browser name for cookie extraction.

    Returns:
        SourceInfo with metadata.

    Raises:
        ProbeError: If yt-dlp fails or metadata is incomplete.
    """
    try:
        info = get_video_info(url, cookies_file=cookies_file, cookies_browser=cookies_browser)
    except ProbeError:
        raise

    # Extract required fields
    title = info.get("title", "Unknown")
    channel = info.get("channel", "Unknown")
    duration = float(info.get("duration", 0))
    description = info.get("description", "")
    video_id = info.get("id", "")

    # Check for subtitles
    has_manual_subs = bool(info.get("subtitles", {}).get("en"))
    has_auto_captions = bool(info.get("automatic_captions", {}).get("en"))

    # Check for authentication requirement via metadata
    requires_auth = info.get("is_live", False) or info.get("availability") == "premium_only"

    return SourceInfo(
        url=url,
        title=title,
        channel=channel,
        duration_seconds=duration,
        duration_formatted=_format_duration(duration),
        description=description,
        has_manual_subs=has_manual_subs,
        has_auto_captions=has_auto_captions,
        requires_auth=requires_auth,
        video_id=video_id,
    )


def probe_source(
    url_or_path: str,
    cookies_file: Optional[str] = None,
    cookies_browser: Optional[str] = None,
) -> SourceInfo:
    """Probe any source (YouTube URL or local file).

    Routes to appropriate prober based on URL scheme.

    Args:
        url_or_path: URL or file path.
        cookies_file: Optional cookies file.
        cookies_browser: Optional browser name.

    Returns:
        SourceInfo.

    Raises:
        ProbeError: If source type is unsupported or probing fails.
    """
    if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
        return probe_youtube(url_or_path, cookies_file=cookies_file, cookies_browser=cookies_browser)
    else:
        raise ProbeError(
            "Local audio/video files are not supported in v0.1. Use YouTube URLs."
        )


# ---------------------------------------------------------------------------
# Environment probing
# ---------------------------------------------------------------------------


def probe_environment() -> EnvProbe:
    """Check availability of tools and environment variables.

    Checks:
    - yt-dlp and ffmpeg via shutil.which()
    - Python packages (whisperx, pyannote, torch) via importlib.util.find_spec()
    - OPENAI_API_KEY and HF_TOKEN env vars

    Returns:
        EnvProbe with boolean flags.
    """
    # Tools
    yt_dlp = shutil.which("yt-dlp") is not None
    ffmpeg = shutil.which("ffmpeg") is not None

    # Python packages
    whisperx = importlib.util.find_spec("whisperx") is not None
    pyannote = importlib.util.find_spec("pyannote") is not None
    torch = importlib.util.find_spec("torch") is not None

    # Environment variables
    openai_api_key = bool(os.environ.get("OPENAI_API_KEY"))
    hf_token = bool(os.environ.get("HF_TOKEN"))

    return EnvProbe(
        yt_dlp=yt_dlp,
        ffmpeg=ffmpeg,
        whisperx=whisperx,
        pyannote=pyannote,
        torch=torch,
        openai_api_key=openai_api_key,
        hf_token=hf_token,
    )


# ---------------------------------------------------------------------------
# Vocabulary probing
# ---------------------------------------------------------------------------


def probe_vocabulary(cwd: Optional[Path] = None) -> VocabProbe:
    """Probe vocabulary files (master + overlays).

    Checks:
    - Master vocabulary at $XDG_DATA_HOME/mdpowers/vocabulary.json
    - Project overlays via walk-up from cwd for .mdpowers/vocabulary.*.json

    Args:
        cwd: Current working directory for overlay walk-up. Defaults to cwd.

    Returns:
        VocabProbe with master path, term counts, and overlay list.
    """
    if cwd is None:
        cwd = Path.cwd()
    else:
        cwd = Path(cwd)

    master_path = None
    master_term_count = 0
    overlay_paths = []
    overlay_term_count = 0

    # Check master vocabulary
    master_candidate = get_mdpowers_data_dir() / "vocabulary.json"
    if master_candidate.is_file():
        master_path = str(master_candidate)
        try:
            vocab_dict = _load_vocab_file(master_candidate)
            master_term_count = len(vocab_dict)
        except Exception:
            # If loading fails, still record the path but count as 0
            master_term_count = 0

    # Walk up for overlays
    current = cwd.resolve()
    while True:
        mdpowers_dir = current / ".mdpowers"
        if mdpowers_dir.is_dir():
            vocab_files = sorted(mdpowers_dir.glob("vocabulary.*.json"))
            for vf in vocab_files:
                overlay_paths.append(str(vf))
                try:
                    vocab_dict = _load_vocab_file(vf)
                    overlay_term_count += len(vocab_dict)
                except Exception:
                    pass

        # Stop at .git or filesystem root
        if (current / ".git").is_dir() or current == current.parent:
            break
        current = current.parent

    return VocabProbe(
        master_path=master_path,
        master_term_count=master_term_count,
        overlay_paths=overlay_paths,
        overlay_term_count=overlay_term_count,
    )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run_probe(
    sources: list[str],
    cwd: Optional[Path] = None,
    cookies_file: Optional[str] = None,
    cookies_browser: Optional[str] = None,
) -> ProbeReport:
    """Run all probes and assemble a ProbeReport.

    Args:
        sources: List of source URLs or paths.
        cwd: Working directory for workspace and vocabulary discovery.
        cookies_file: Optional cookies file for yt-dlp.
        cookies_browser: Optional browser name for yt-dlp.

    Returns:
        ProbeReport with all three probes and context info.

    Raises:
        ProbeError: If any source probing fails.
    """
    if cwd is None:
        cwd = Path.cwd()
    else:
        cwd = Path(cwd)

    # Probe sources
    source_infos = []
    for src in sources:
        source_infos.append(
            probe_source(src, cookies_file=cookies_file, cookies_browser=cookies_browser)
        )

    # Probe environment
    env = probe_environment()

    # Probe vocabulary
    vocab = probe_vocabulary(cwd=cwd)

    # Get host mode and workspace root
    host_mode = detect_host_mode()
    workspace_root = str(find_workspace_root(cwd=cwd))

    return ProbeReport(
        sources=source_infos,
        env=env,
        vocab=vocab,
        host_mode=host_mode,
        workspace_root=workspace_root,
    )


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------


def format_probe_report(report: ProbeReport) -> str:
    """Pretty-print a ProbeReport as readable text.

    Uses checkmarks and crosses to indicate availability.

    Args:
        report: ProbeReport to format.

    Returns:
        Formatted string (not JSON).
    """
    lines = []

    # Sources
    lines.append("Sources:")
    if not report.sources:
        lines.append("  (none)")
    for src in report.sources:
        manual = "yes" if src.has_manual_subs else "no"
        auto = "yes" if src.has_auto_captions else "no"
        auth = ", auth required" if src.requires_auth else ""
        lines.append(
            f"  - [YouTube] \"{src.title}\" ({src.duration_formatted}, "
            f"manual subs: {manual}, auto: {auto}{auth})"
        )

    # Environment
    lines.append("Environment:")
    check = "✓" if report.env.yt_dlp else "✗"
    lines.append(f"  - yt-dlp: {check}")
    check = "✓" if report.env.ffmpeg else "✗"
    lines.append(f"  - ffmpeg: {check}")
    if not report.env.whisperx:
        lines.append("  - whisperx: ✗ (not installed)")
    else:
        lines.append("  - whisperx: ✓")
    if not report.env.pyannote:
        lines.append("  - pyannote: ✗ (not installed)")
    else:
        lines.append("  - pyannote: ✓")
    if not report.env.torch:
        lines.append("  - torch: ✗ (not installed)")
    else:
        lines.append("  - torch: ✓")
    check = "✓" if report.env.openai_api_key else "✗"
    lines.append(f"  - OPENAI_API_KEY: {check}")
    check = "✓" if report.env.hf_token else "✗"
    lines.append(f"  - HF_TOKEN: {check}")

    # Vocabulary
    lines.append("Vocabulary:")
    if report.vocab.master_path:
        check = "✓"
        lines.append(f"  - Global master: {check} ({report.vocab.master_term_count} terms)")
    else:
        lines.append("  - Global master: ✗")
    if report.vocab.overlay_paths:
        check = "✓"
        count = report.vocab.overlay_term_count
        lines.append(f"  - Project overlay(s): {check} ({count} total terms)")
        for path in report.vocab.overlay_paths:
            lines.append(f"      - {path}")
    else:
        lines.append("  - Project overlay: ✗")

    # Context
    lines.append(f"Host mode: {report.host_mode}")
    lines.append(f"Workspace root: {report.workspace_root}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Probe source URL and environment for mdpowers transcribe skill."
    )
    parser.add_argument("urls", nargs="+", help="Source URL(s) to probe (YouTube URLs in v0.1)")
    parser.add_argument("--cookies-file", help="Path to cookies.txt for yt-dlp")
    parser.add_argument(
        "--cookies-from-browser",
        help="Browser name for yt-dlp cookie extraction (e.g., firefox, chrome)",
    )
    parser.add_argument("--cwd", help="Working directory for workspace discovery (optional)")

    args = parser.parse_args()

    try:
        cwd = Path(args.cwd) if args.cwd else None
        report = run_probe(
            sources=args.urls,
            cwd=cwd,
            cookies_file=args.cookies_file,
            cookies_browser=args.cookies_from_browser,
        )
        print(format_probe_report(report))
    except ProbeError as e:
        print(f"Probe error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
