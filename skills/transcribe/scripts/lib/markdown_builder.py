"""Markdown building utilities — frontmatter, path resolution, output handling."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .errors import TranscribeError
from .ytdlp_helpers import safe_filename


def format_time(seconds: float) -> str:
    """
    Format seconds to HH:MM:SS.ss timestamp.

    Args:
        seconds: Duration in seconds (float).

    Returns:
        Formatted time string like "01:23:45.67".
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.2f}"


def build_frontmatter(**fields) -> str:
    """
    Build YAML frontmatter from keyword arguments.

    Required fields: title, source, channel, published, duration, transcript_method,
    pathway, quality, transcribed_at.

    Optional fields: quality_notes, vocab_master_version, vocab_overlay, host,
    co_host, guest, guests, speakers.

    List fields (guests, speakers) are formatted as YAML lists with proper indentation.
    String fields are quoted if they contain special YAML characters.

    Args:
        **fields: Key-value pairs for frontmatter.

    Returns:
        Formatted frontmatter string like "---\nkey: value\n---\n".
    """
    lines = ["---"]

    # Define field order: required first, then optional
    required_order = [
        "title",
        "source",
        "channel",
        "published",
        "duration",
        "transcript_method",
        "pathway",
        "quality",
        "transcribed_at",
    ]
    optional_order = [
        "quality_notes",
        "vocab_master_version",
        "vocab_overlay",
        "host",
        "co_host",
        "guest",
        "guests",
        "speakers",
    ]

    # Process required fields
    for key in required_order:
        if key in fields:
            value = fields[key]
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_yaml_quote(str(item))}")
            else:
                lines.append(f"{key}: {_yaml_quote(str(value))}")

    # Process optional fields
    for key in optional_order:
        if key in fields:
            value = fields[key]
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {_yaml_quote(str(item))}")
            else:
                lines.append(f"{key}: {_yaml_quote(str(value))}")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _yaml_quote(value: str) -> str:
    """
    Quote a string if it contains special YAML characters.

    Args:
        value: String to potentially quote.

    Returns:
        Quoted string if needed, otherwise original string.
    """
    special_chars = [":", "#", "[", "]", "{", "}", ",", "&", "*", "-", "|", ">", '"', "'", "%"]
    if any(char in value for char in special_chars) or value.strip() != value:
        return f'"{value}"'
    return value


def build_path1_markdown(
    title: str,
    description: str,
    summary: str,
    segments: list[dict],
    frontmatter_dict: dict,
) -> str:
    """
    Build Path 1 (YouTube subtitles) markdown output.

    No speaker identification. Each segment appears as a timestamped line:
    [HH:MM.ss] text

    Args:
        title: Document title.
        description: Brief description of the content.
        summary: LLM-generated summary of the transcript.
        segments: List of dicts with 'start', 'end', 'text' keys.
        frontmatter_dict: Dict of frontmatter key-value pairs (passed to build_frontmatter).

    Returns:
        Complete markdown string with frontmatter, description, summary, and segments.
    """
    frontmatter = build_frontmatter(**frontmatter_dict)

    lines = [frontmatter]

    if description:
        lines.append(f"## Description\n\n{description}\n")

    if summary:
        lines.append(f"## Summary\n\n{summary}\n")

    lines.append("## Transcript\n")

    for seg in segments:
        start = seg.get("start", 0)
        text = seg.get("text", "").strip()
        if text:
            timestamp = format_time(start)
            # Convert HH:MM:SS.ss to HH:MM.ss for path1 output
            parts = timestamp.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = parts
                timestamp = f"{hours}:{minutes}.{seconds.split('.')[1] if '.' in seconds else '00'}"
            lines.append(f"[{timestamp}] {text}")

    return "\n".join(lines) + "\n"


def build_path2_markdown(
    title: str,
    description: str,
    summary: str,
    segments: list[dict],
    frontmatter_dict: dict,
) -> str:
    """
    Build Path 2 (diarized) markdown output.

    Segments are grouped by speaker. Each speaker block appears as:
    **Speaker Name** [HH:MM.ss]
    <text on next line>

    Args:
        title: Document title.
        description: Brief description of the content.
        summary: LLM-generated summary of the transcript.
        segments: List of dicts with 'start', 'end', 'text', 'speaker' keys.
        frontmatter_dict: Dict of frontmatter key-value pairs (passed to build_frontmatter).

    Returns:
        Complete markdown string with frontmatter, description, summary, and speaker blocks.
    """
    frontmatter = build_frontmatter(**frontmatter_dict)

    lines = [frontmatter]

    if description:
        lines.append(f"## Description\n\n{description}\n")

    if summary:
        lines.append(f"## Summary\n\n{summary}\n")

    lines.append("## Transcript\n")

    # Group consecutive same-speaker segments
    current_speaker = None
    current_block = []

    for seg in segments:
        speaker = seg.get("speaker", "UNKNOWN")
        text = seg.get("text", "").strip()

        if speaker != current_speaker:
            # Flush current block if any
            if current_block and current_speaker:
                timestamp = format_time(current_block[0].get("start", 0))
                parts = timestamp.split(":")
                if len(parts) == 3:
                    hours, minutes, seconds = parts
                    timestamp = f"{hours}:{minutes}.{seconds.split('.')[1] if '.' in seconds else '00'}"
                block_text = " ".join(s.get("text", "").strip() for s in current_block)
                lines.append(f"**{current_speaker}** [{timestamp}]")
                lines.append(block_text)
                lines.append("")

            current_speaker = speaker
            current_block = []

        if text:
            current_block.append(seg)

    # Flush final block
    if current_block and current_speaker:
        timestamp = format_time(current_block[0].get("start", 0))
        parts = timestamp.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = parts
            timestamp = f"{hours}:{minutes}.{seconds.split('.')[1] if '.' in seconds else '00'}"
        block_text = " ".join(s.get("text", "").strip() for s in current_block)
        lines.append(f"**{current_speaker}** [{timestamp}]")
        lines.append(block_text)
        lines.append("")

    return "\n".join(lines) + "\n"


def resolve_output_path(
    source_id: str,
    title: str,
    cwd: Optional[Path] = None,
    user_specified: Optional[Path] = None,
) -> Path:
    """
    Resolve output path for transcript markdown file.

    If user_specified is provided, use it (as is, no validation).
    Otherwise, generate path as: {cwd}/transcripts/{date}_{safe_title}_{source_id}.md

    Creates the transcripts directory if needed.

    Args:
        source_id: Source identifier (e.g., "yt_abc123").
        title: Document title, to be sanitized for filename.
        cwd: Current working directory. Defaults to Path.cwd().
        user_specified: Optional user-provided output path.

    Returns:
        Resolved Path object.

    Raises:
        TranscribeError: If directory creation fails.
    """
    if user_specified:
        return Path(user_specified)

    if cwd is None:
        cwd = Path.cwd()

    cwd = Path(cwd)
    transcripts_dir = cwd / "transcripts"

    try:
        transcripts_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise TranscribeError(f"Failed to create transcripts directory: {e}")

    # Build filename: YYYY-MM-DD_safe_title_source_id.md
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_title = safe_filename(title, max_len=60)
    filename = f"{date_str}_{safe_title}_{source_id}.md"

    return transcripts_dir / filename


def handle_overwrite_conflict(path: Path) -> Path:
    """
    Handle file overwrite conflicts by renaming to versioned path.

    If path exists, returns path with _v2 suffix inserted before .md.
    If _v2 exists, tries _v3, _v4, etc. until finding an available name.

    Args:
        path: The original path.

    Returns:
        Either the original path (if it doesn't exist) or a versioned variant.
    """
    if not path.exists():
        return path

    # Increment version number until we find an available path
    stem = path.stem  # e.g., "2024-01-15_my_transcript_yt_abc"
    suffix = path.suffix  # e.g., ".md"
    parent = path.parent

    version = 2
    while True:
        versioned_name = f"{stem}_v{version}{suffix}"
        versioned_path = parent / versioned_name
        if not versioned_path.exists():
            return versioned_path
        version += 1


def rename_broken(path: Path) -> Path:
    """
    Rename a file from .md to .broken.md.

    Args:
        path: Path to the file to rename.

    Returns:
        Path to the renamed file.

    Raises:
        TranscribeError: If rename fails.
    """
    if not path.exists():
        raise TranscribeError(f"File does not exist: {path}")

    broken_path = path.parent / f"{path.stem}.broken{path.suffix}"
    try:
        path.rename(broken_path)
        return broken_path
    except OSError as e:
        raise TranscribeError(f"Failed to rename {path} to {broken_path}: {e}")
