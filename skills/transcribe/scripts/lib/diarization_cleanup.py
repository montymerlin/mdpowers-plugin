"""Diarization cleanup utilities — merge short speaker blocks, validate counts."""

import re
from typing import Optional, Tuple


def merge_short_speaker_blocks(segments: list[dict], min_words: int = 4) -> list[dict]:
    """
    Collapse speaker blocks shorter than min_words into the adjacent
    block with the most words. Runs up to 3 passes to handle cascading merges.

    A "speaker block" is a maximal run of consecutive segments from the same
    speaker. This function identifies short blocks (fewer than min_words total)
    and reassigns them to the neighboring block with more words.

    Args:
        segments: List of dicts, each with 'speaker' and 'text' keys.
        min_words: Minimum word count to keep a speaker block. Blocks below
                   this threshold will be merged into neighbors.

    Returns:
        Modified segments list with short blocks merged.
    """
    if len(segments) < 2:
        return segments

    for _ in range(3):
        # Group consecutive same-speaker segments into runs
        runs: list[list[dict]] = []
        for seg in segments:
            if runs and runs[-1][-1]["speaker"] == seg["speaker"]:
                runs[-1].append(seg)
            else:
                runs.append([seg])

        changed = False
        for i, run in enumerate(runs):
            # Count words in this run
            wc = sum(len(s["text"].split()) for s in run)
            if wc >= min_words:
                continue

            # Calculate word counts for neighbors
            prev_wc = sum(len(s["text"].split()) for s in runs[i - 1]) if i > 0 else 0
            next_wc = sum(len(s["text"].split()) for s in runs[i + 1]) if i < len(runs) - 1 else 0

            # Skip if no valid neighbors
            if prev_wc == 0 and next_wc == 0:
                continue

            # Pick the neighbor with more words
            target_spk = (
                runs[i - 1][-1]["speaker"]
                if prev_wc >= next_wc
                else runs[i + 1][0]["speaker"]
            )

            # Reassign all segments in short run
            for s in run:
                s["speaker"] = target_spk
            changed = True

        if not changed:
            break

    return segments


def validate_speaker_count(
    segments: list[dict],
    expected: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Check speaker count against expected value.

    Counts unique speakers in the segments (excluding empty or "UNKNOWN"),
    then validates against an optional expected count.

    Args:
        segments: List of dicts, each with optional 'speaker' key.
        expected: Optional expected speaker count to validate against.
                  If None, only returns the detected count.

    Returns:
        Tuple of (valid: bool, message: str).
        - valid is True if expected is None or matches actual.
        - message describes the count and any mismatch.
    """
    # Extract unique speakers, excluding empty and "UNKNOWN"
    unique = {
        s.get("speaker", "")
        for s in segments
        if s.get("speaker") and s["speaker"] != "UNKNOWN"
    }
    actual = len(unique)

    if expected is None:
        return True, f"{actual} speakers detected"

    if actual == expected:
        return True, f"{actual} speakers detected (matches expected)"
    elif actual < expected:
        return (
            False,
            f"Expected {expected} speakers but only found {actual} — "
            "diarization may have collapsed speakers",
        )
    else:
        return (
            False,
            f"Expected {expected} speakers but found {actual} — "
            "diarization may have over-split",
        )
