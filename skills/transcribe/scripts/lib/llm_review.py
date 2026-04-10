"""LLM review utilities — summary generation, quirks detection, auto-correction."""

from typing import Optional

from .errors import TranscribeError


def generate_summary(
    client,
    title: str,
    segments: list[dict],
    speaker_names: Optional[list] = None,
) -> str:
    """
    Generate a summary of the transcript using LLM (gpt-4o-mini).

    Truncates transcript to first ~6000 words. Includes speaker names in the
    prompt if provided (for diarized transcripts).

    Args:
        client: OpenAI client (with model gpt-4o-mini available).
        title: Document title.
        segments: List of dicts with 'text' key.
        speaker_names: Optional list of speaker names (for diarized content).

    Returns:
        Summary as a single paragraph (3-5 sentences).

    Raises:
        TranscribeError: If LLM request fails.
    """
    # Serialize segments to plain text, limit to ~6000 words
    transcript_text = _strip_speaker_blocks_for_prompt(segments)
    if len(transcript_text) > 24000:  # ~6000 words * 4 chars/word
        transcript_text = transcript_text[:24000]

    # Build prompt
    prompt = f"Title: {title}\n\n"
    if speaker_names:
        prompt += f"Speakers: {', '.join(speaker_names)}\n\n"
    prompt += f"Transcript:\n{transcript_text}\n\n"
    prompt += (
        "Write a concise summary of this transcript in 3-5 sentences. "
        "Focus on key themes, conclusions, and main takeaways."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise TranscribeError(f"LLM summary generation failed: {e}")


def llm_quirks_review(
    client,
    title: str,
    segments: list[dict],
    speaker_names: Optional[list[str]] = None,
) -> dict:
    """
    Review transcript for quirks and potential corrections using LLM.

    Returns suggestions for common speech transcription issues:
    - Speaker name corrections (if diarized)
    - Stutters, filler words, repeated phrases
    - Probable typos or mishearings

    Args:
        client: OpenAI client.
        title: Document title.
        segments: List of dicts with 'text' key (and optional 'speaker' key).
        speaker_names: Optional list of expected speaker names (for validation).

    Returns:
        Dict with keys:
        - auto_corrections: list of {location, original, suggestion, confidence}
        - ambiguous: list of potential issues flagged for manual review
    """
    # Serialize segments for prompt
    transcript_excerpt = _strip_speaker_blocks_for_prompt(segments)

    prompt = f"""Review this transcript excerpt for speech transcription quirks and corrections.

Title: {title}
"""
    if speaker_names:
        prompt += f"Expected speakers: {', '.join(speaker_names)}\n"

    prompt += f"""
Transcript:
{transcript_excerpt}

Return a JSON object with:
{{
  "auto_corrections": [
    {{"location": "where found (e.g., 'Speaker A around 2:30')", "original": "original text", "suggestion": "corrected text", "confidence": 0.95}}
  ],
  "ambiguous": [
    {{"location": "where found", "issue": "description of potential problem"}}
  ]
}}

Focus on:
- Speaker names (if provided, check they match)
- Stutters and repeated words
- Filler words (um, uh, like, you know)
- Obvious phonetic errors or mishearings
- Incomplete sentences that might need fixing

Return ONLY the JSON object, no other text."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        import json

        result_text = response.choices[0].message.content.strip()
        return json.loads(result_text)
    except Exception as e:
        raise TranscribeError(f"LLM quirks review failed: {e}")


def apply_llm_quirk_autocorrections(
    segments: list[dict],
    corrections: list[dict],
    conf_threshold: float = 0.90,
    len_threshold: int = 180,
) -> int:
    """
    Apply high-confidence LLM corrections to segments.

    Only applies corrections with:
    - confidence >= conf_threshold
    - replacement text length < len_threshold (to avoid overwriting large sections)

    Args:
        segments: List of dicts with 'text' key.
        corrections: List of dicts from llm_quirks_review["auto_corrections"].
        conf_threshold: Minimum confidence to apply correction (0-1).
        len_threshold: Maximum character length of replacement text.

    Returns:
        Number of corrections actually applied.
    """
    applied = 0

    for correction in corrections:
        confidence = correction.get("confidence", 0)
        original = correction.get("original", "")
        suggestion = correction.get("suggestion", "")

        # Skip low-confidence or long replacements
        if confidence < conf_threshold or len(suggestion) >= len_threshold:
            continue

        # Find and replace in segments
        for seg in segments:
            text = seg.get("text", "")
            if original in text:
                seg["text"] = text.replace(original, suggestion)
                applied += 1
                break  # Only replace first occurrence

    return applied


def _clip_to_token_budget(text: str, max_tokens: int) -> str:
    """
    Truncate text to fit within a token budget.

    Attempts to use tiktoken cl100k_base encoding. Falls back to character-based
    approximation (4 chars per token) if tiktoken is not available.

    Args:
        text: The text to truncate.
        max_tokens: Maximum number of tokens allowed.

    Returns:
        Truncated text that fits within the token budget.
    """
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("cl100k_base")
        tokens = encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        truncated_tokens = tokens[:max_tokens]
        return encoding.decode(truncated_tokens)
    except ImportError:
        # Fallback: approximate 4 chars per token
        char_limit = max_tokens * 4
        if len(text) <= char_limit:
            return text
        return text[:char_limit]


def _strip_speaker_blocks_for_prompt(segments: list[dict]) -> str:
    """
    Serialize segments to [SPEAKER_XX] text format for LLM prompts.

    Merges consecutive segments from the same speaker into single lines.
    Caps output at first ~12000 characters.

    Args:
        segments: List of dicts with 'text' key (and optional 'speaker' key).

    Returns:
        String formatted as "[SPEAKER_XX] text\n[SPEAKER_XX] text\n...".
    """
    lines = []
    current_speaker = None
    current_text = []

    for seg in segments:
        speaker = seg.get("speaker", "UNKNOWN")
        text = seg.get("text", "").strip()

        if not text:
            continue

        if speaker != current_speaker:
            # Flush current block
            if current_speaker is not None and current_text:
                merged_text = " ".join(current_text)
                lines.append(f"[{current_speaker}] {merged_text}")
            current_speaker = speaker
            current_text = []

        current_text.append(text)

    # Flush final block
    if current_speaker is not None and current_text:
        merged_text = " ".join(current_text)
        lines.append(f"[{current_speaker}] {merged_text}")

    result = "\n".join(lines)

    # Cap at ~12000 chars
    if len(result) > 12000:
        result = result[:12000] + "\n[... transcript truncated ...]"

    return result
