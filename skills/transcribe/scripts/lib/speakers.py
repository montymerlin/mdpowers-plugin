"""Speaker identification and role assignment for transcripts.

Provides speaker metadata research, LLM-based transcript guessing, overlap-based
speaker assignment, and speaker role resolution (host, co-host, guest). Used by
the mdpowers transcribe skill to map diarization labels to real names and build
YAML frontmatter with speaker roles.
"""

import json
from typing import Optional
from pathlib import Path

from .errors import SpeakerError


# Speaker identification token budget for transcript sampling
TRANSCRIPT_SAMPLE_TOKENS = 8000


def research_speakers_from_metadata(
    client,
    title: str,
    description: str,
    num_speakers: int
) -> list[str]:
    """
    Extract likely speaker names from video metadata alone.

    Uses the video title and description (not transcript) to find speaker names
    that are often embedded in podcast episode titles (e.g. 'Episode N: Topic
    with Guest Name'). This provides a grounded prior before running the less-
    reliable in-transcript search.

    Args:
        client: OpenAI client instance.
        title: Video title.
        description: Video description.
        num_speakers: Expected number of speakers (used as a hint).

    Returns:
        List of speaker names extracted from metadata. Empty list if none found.

    Raises:
        No exceptions raised; returns empty list on error.
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are extracting speaker names from a video title and description. "
                    "Podcast episode titles often contain 'with <Guest Name>' or 'featuring <Name>'. "
                    "Return ONLY JSON: {\"names\": [\"Name1\", \"Name2\"]}. "
                    "Only include names you are highly confident appear as participants. "
                    "Return an empty list if unsure — do not guess."
                ),
            },
            {
                "role": "user",
                "content": (
                    f'Title: "{title}"\n\n'
                    f'Description (first 1200 chars):\n{description[:1200]}\n\n'
                    f'Expected number of speakers: {num_speakers}'
                ),
            },
        ],
        max_tokens=150,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(response.choices[0].message.content).get("names", [])
    except Exception:
        return []


def guess_speakers(
    client,
    title: str,
    description: str,
    segments: list[dict],
    known_names: Optional[list[str]] = None
) -> dict[str, str]:
    """
    Map diarization speaker labels to real names using transcript excerpt.

    Uses title + description as primary context, then scans the transcript for
    direct self-introductions ('I'm X', 'my name is X') and direct address
    ('Thanks, John'). Does NOT assign names based on third-party mentions.

    Args:
        client: OpenAI client instance.
        title: Video title.
        description: Video description.
        segments: Transcript segments with 'speaker', 'text', 'start', 'end' keys.
        known_names: Optional list of confirmed participant names (prioritized).

    Returns:
        Dict mapping diarization labels (SPEAKER_XX) to real names.
        Returns empty dict on error or if no confident mappings found.
    """
    # Build transcript sample with speaker labels (first ~2500 words)
    lines: list[str] = []
    current, count = None, 0
    for seg in segments:
        spk = seg.get("speaker", "")
        text = seg.get("text", "").strip()
        if not text:
            continue
        if spk != current:
            lines.append(f"\n[{spk}]: {text}")
            current = spk
        else:
            lines[-1] += " " + text
        count += len(text.split())
        if count > 2500:
            break
    sample = "\n".join(lines)

    known_hint = ""
    if known_names:
        known_hint = (
            f"\n\nKnown participants confirmed from metadata: {', '.join(known_names)}. "
            "Your primary job is to map these names to the correct SPEAKER_XX labels."
        )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are mapping diarization speaker labels (SPEAKER_00, SPEAKER_01, etc.) "
                    "to real person names in a podcast transcript.\n\n"
                    "CRITICAL RULES — follow these exactly:\n"
                    "1. A speaker label should only be assigned a name if that speaker INTRODUCES "
                    "THEMSELVES ('I'm X', 'my name is X', 'I'm X from Y') OR is DIRECTLY ADDRESSED "
                    "by name by another speaker ('Thanks, John', 'Great point, Sarah').\n"
                    "2. DO NOT assign a name simply because it appears in the text. Names of "
                    "colleagues, third parties, companies, and people being discussed are NOT the "
                    "speaker's name.\n"
                    "3. If known participants are provided, prioritise mapping those names.\n"
                    "4. Return ONLY a JSON object mapping labels to names.\n"
                    "5. Omit any mapping you are not confident about."
                ),
            },
            {
                "role": "user",
                "content": (
                    f'Podcast title: "{title}"\n'
                    f'Description: {description[:600]}'
                    f'{known_hint}\n\n'
                    f'Transcript excerpt (first ~10 min):\n{sample}'
                ),
            },
        ],
        max_tokens=200,
        response_format={"type": "json_object"},
    )
    try:
        return json.loads(response.choices[0].message.content)
    except Exception:
        return {}


def assign_speakers_overlap(
    transcript_segments: list[dict],
    diarization: list[dict]
) -> list[dict]:
    """
    Assign diarization speaker labels to transcript segments by time overlap.

    Calculates the amount of time overlap between each transcript segment and
    each diarization speaker interval. Assigns the segment to the speaker with
    the most overlap. Falls back to nearest-midpoint (within 5s tolerance) if
    there is no overlap.

    This avoids the "bleeding artefact" where the last/first words of a turn
    are assigned to the wrong speaker because the segment midpoint falls just
    inside the wrong diarization interval.

    Args:
        transcript_segments: List of segments with 'start', 'end', 'text' keys.
        diarization: List of diarization intervals with 'start', 'end', 'speaker'.

    Returns:
        Input segments with 'speaker' key added/updated.
    """
    result = []
    for seg in transcript_segments:
        s_start, s_end = seg["start"], seg["end"]

        # Sum overlap with each speaker
        speaker_overlap: dict[str, float] = {}
        for d in diarization:
            overlap = max(0.0, min(s_end, d["end"]) - max(s_start, d["start"]))
            if overlap > 0:
                spk = d["speaker"]
                speaker_overlap[spk] = speaker_overlap.get(spk, 0.0) + overlap

        if speaker_overlap:
            best_speaker = max(speaker_overlap, key=speaker_overlap.get)
        else:
            # No overlap — nearest by midpoint, within 5s tolerance
            s_mid = (s_start + s_end) / 2
            best_dist, best_speaker = float("inf"), "UNKNOWN"
            for d in diarization:
                dist = abs((d["start"] + d["end"]) / 2 - s_mid)
                if dist < best_dist:
                    best_dist, best_speaker = dist, d["speaker"]
            if best_dist >= 5.0:
                best_speaker = "UNKNOWN"

        result.append({**seg, "speaker": best_speaker})
    return result


def map_speakers_by_order(
    segments: list[dict],
    names: list[str]
) -> dict[str, str]:
    """
    Map speaker labels to names by order of first appearance.

    Used when speaker names are provided via command-line (--speakers flag),
    bypassing GPT guessing. Assigns names in the order that diarization labels
    first appear in the transcript.

    Args:
        segments: Transcript segments with 'speaker' key.
        names: List of speaker names in appearance order.

    Returns:
        Dict mapping diarization labels (SPEAKER_XX) to names. Includes the
        label itself as fallback if there are more unique speakers than names.
    """
    seen: dict[str, int] = {}
    for seg in segments:
        spk = seg.get("speaker", "")
        if spk and spk not in seen and spk != "UNKNOWN":
            seen[spk] = len(seen)
    mapping = {}
    for spk, idx in seen.items():
        mapping[spk] = names[idx] if idx < len(names) else spk
    return mapping


def merge_by_role(speaker_names: list[str]) -> dict:
    """
    Resolve a flat list of speaker names into frontmatter-ready role structure.

    Maps speakers to semantic roles (host, co_host, guest, guests) for
    embedding in YAML frontmatter. Assumes order: [host, co-host, guests...].

    Args:
        speaker_names: List of speaker names.

    Returns:
        Dict with role keys ('host', 'co_host', 'guest', or 'guests') for
        YAML frontmatter embedding. Empty dict if input is empty.

    Examples:
        >>> merge_by_role(['Alice'])
        {'host': 'Alice'}
        >>> merge_by_role(['Alice', 'Bob'])
        {'host': 'Alice', 'co_host': 'Bob'}
        >>> merge_by_role(['Alice', 'Bob', 'Charlie'])
        {'host': 'Alice', 'co_host': 'Bob', 'guest': 'Charlie'}
        >>> merge_by_role(['Alice', 'Bob', 'Charlie', 'Dave'])
        {'host': 'Alice', 'co_host': 'Bob', 'guests': ['Charlie', 'Dave']}
    """
    if not speaker_names:
        return {}

    result = {}

    if len(speaker_names) >= 1:
        result["host"] = speaker_names[0]

    if len(speaker_names) >= 2:
        result["co_host"] = speaker_names[1]

    if len(speaker_names) > 2:
        guests = speaker_names[2:]
        if len(guests) == 1:
            result["guest"] = guests[0]
        else:
            result["guests"] = guests

    return result
