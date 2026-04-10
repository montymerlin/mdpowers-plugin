#!/usr/bin/env python3
"""Path 3 — API service transcription (STUB for v0.1).

This pathway is not yet implemented. When invoked, it raises NotYetImplemented
with a clear message directing users to Path 1 or Path 2.

v0.2 will implement this using an API-based transcription service (likely
AssemblyAI) for fast multi-speaker transcription at ~$0.37/hour.

See references/pathways/P3-api-service.md for the full roadmap.
"""

import sys
from pathlib import Path


class NotYetImplemented(NotImplementedError):
    """Raised when Path 3 is invoked in v0.1."""
    pass


def run(source: str, **kwargs) -> Path:
    """Path 3 runner — raises NotYetImplemented in v0.1.

    Args:
        source: YouTube URL or file path.
        **kwargs: Ignored in v0.1.

    Raises:
        NotYetImplemented: Always, with guidance on alternatives.
    """
    raise NotYetImplemented(
        "Path 3 (API service) is not yet implemented in v0.1.\n\n"
        "Available alternatives:\n"
        "  - Path 1 (YouTube fast): single-speaker YouTube content, <5 min\n"
        "    Use: --pathway fast\n"
        "  - Path 2 (WhisperX local): multi-speaker content, 45min-2h\n"
        "    Use: --pathway local\n\n"
        "See references/pathways/P3-api-service.md for the v0.2 roadmap.\n"
        "Likely service: AssemblyAI (~$0.37/hour, diarization included)."
    )


def main():
    """CLI entry point — prints error and exits."""
    print(
        "Error: Path 3 (API service) is not yet implemented in v0.1.\n"
        "Use --pathway fast or --pathway local instead.",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
