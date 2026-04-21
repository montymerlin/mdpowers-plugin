"""Vocabulary module — loading, flattening, merging, and management.

This module handles all vocabulary-related functionality for the transcribe skill:
- Loading vocabulary files from the XDG discovery cascade (master + overlay)
- Flattening categorized vocabulary into lookup dicts
- Priming Whisper with concise term lists via token budgets
- Post-correcting transcripts using substring replacement with case preservation
- Discovering vocabulary candidates from segments (acronyms, proper nouns, unusual words)
- GPT assessment of candidates
- Writing vocabulary review files for human curation
- Promoting terms from overlay to master vocabulary
- Adding new terms to any vocabulary file

The vocabulary discovery cascade supports:
1. $MDPOWERS_VOCAB env var for explicit override
2. $XDG_DATA_HOME/mdpowers/vocabulary.json (master vocabulary)
3. Walk-up from cwd through parent directories looking for .mdpowers/vocabulary.*.json
   (deeper levels override shallower ones; all are merged beneath master)
4. Explicit overlay_path parameter (skips walk-up)

Vocabulary files use JSON with this structure:
{
  "_meta": {
    "description": "...",
    "updated": "YYYY-MM-DD",
    ...
  },
  "category_name": {
    "CorrectTerm": {
      "mistranscriptions": ["variant1", "variant2"],
      "context": "Optional note about usage"
    },
    ...
  },
  ...
}

Both entry shapes (list or dict) are supported during loading:
- Old shape: "term": ["mistake1", "mistake2"]
- Current shape: "term": {"mistranscriptions": [...], "context": "..."}
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from .errors import VocabularyError
from .host_mode import get_mdpowers_data_dir


# ---------------------------------------------------------------------------
# Core vocabulary I/O and flattening
# ---------------------------------------------------------------------------


def _flatten_vocab_data(data: dict) -> dict[str, list[str]]:
    """Flatten categorized vocabulary JSON into lookup dict.

    Skips _meta key. Handles both list and dict entry shapes:
    - List: "term": ["mistake1", "mistake2"] -> flattened to [term, ...mistakes]
    - Dict: "term": {"mistranscriptions": [...], "context": "..."} -> flattened to [term, ...mistakes]

    Args:
        data: Raw vocabulary JSON dict (with categories and _meta).

    Returns:
        Flat dict mapping each term/mistranscription to itself as a key-value pair.
        Example: {"ReFi": ["ReFi"], "rfi": ["ReFi"], "reef": ["ReFi"]}
    """
    flattened = {}

    for category, entries in data.items():
        if category == "_meta":
            continue
        if not isinstance(entries, dict):
            continue

        for term, value in entries.items():
            # Extract mistranscriptions from either shape
            if isinstance(value, list):
                mistakes = value
            elif isinstance(value, dict):
                mistakes = value.get("mistranscriptions", [])
            else:
                mistakes = []

            # All variants (correct term + all mistakes) map to themselves
            all_variants = [term] + mistakes
            for variant in all_variants:
                if variant not in flattened:
                    flattened[variant] = []
                # Ensure term is in the list for this variant
                if term not in flattened[variant]:
                    flattened[variant].append(term)

    return flattened


def _load_vocab_file(vocab_path: Path) -> dict[str, list[str]]:
    """Load and flatten a single vocabulary file.

    Args:
        vocab_path: Path to vocabulary JSON file.

    Returns:
        Flattened vocabulary dict.

    Raises:
        VocabularyError: If file doesn't exist or JSON is malformed.
    """
    if not vocab_path.is_file():
        raise VocabularyError(f"Vocabulary file not found: {vocab_path}")

    try:
        data = json.loads(vocab_path.read_text())
    except json.JSONDecodeError as e:
        raise VocabularyError(f"Malformed vocabulary JSON in {vocab_path}: {e}")

    return _flatten_vocab_data(data)


def load_vocabulary(
    overlay_path: Optional[Path] = None, cwd: Optional[Path] = None
) -> tuple[dict[str, list[str]], dict]:
    """Load vocabulary using the XDG discovery cascade.

    Discovery order (merging so later sources override earlier):
    1. Empty merged dict
    2. $MDPOWERS_VOCAB env var (if set) → load as master
    3. $XDG_DATA_HOME/mdpowers/vocabulary.json (platform-specific master)
    4. If overlay_path NOT explicitly provided: walk up from cwd looking for
       .mdpowers/vocabulary.*.json at each level (deepest level wins on conflicts)
    5. If overlay_path explicitly provided: skip walk-up and load only this

    Merge semantics: overlay keys REPLACE master keys (not union).

    Args:
        overlay_path: Optional explicit overlay file. If provided, skips walk-up.
        cwd: Current working directory for walk-up search. Defaults to Path.cwd().

    Returns:
        Tuple of (flattened_vocab_dict, meta_dict) where meta_dict contains:
        - "master_version": version from master _meta.updated
        - "overlay": path to overlay file (if loaded)
        - "overlay_version": version from overlay _meta.updated (if loaded)
        - "master_path": path to master file
        - "overlay_path": path to overlay file (if loaded)

    Raises:
        VocabularyError: If master or overlay files are malformed.
    """
    if cwd is None:
        cwd = Path.cwd()
    else:
        cwd = Path(cwd)

    merged = {}
    meta = {
        "master_version": None,
        "overlay": None,
        "overlay_version": None,
        "master_path": None,
        "overlay_path": None,
    }

    # 1. Find and load master vocabulary
    master_path = None

    # Check explicit env var override
    env_vocab = os.environ.get("MDPOWERS_VOCAB")
    if env_vocab:
        master_path = Path(env_vocab)
    else:
        # Check XDG default
        xdg_path = get_mdpowers_data_dir() / "vocabulary.json"
        if xdg_path.is_file():
            master_path = xdg_path

    if master_path and master_path.is_file():
        try:
            master_data = json.loads(master_path.read_text())
            merged.update(_flatten_vocab_data(master_data))
            meta["master_version"] = (
                master_data.get("_meta", {}).get("updated", "unknown")
            )
            meta["master_path"] = str(master_path)
        except json.JSONDecodeError as e:
            raise VocabularyError(f"Malformed master vocabulary JSON in {master_path}: {e}")

    # 2. Find and load overlay(s)
    overlay_files = []

    if overlay_path:
        # Explicit overlay: skip walk-up
        if overlay_path.is_file():
            overlay_files = [overlay_path]
    else:
        # Walk-up discovery: look for .mdpowers/vocabulary.*.json at each level
        # Stop at .git or filesystem root
        current = cwd.resolve()
        while True:
            mdpowers_dir = current / ".mdpowers"
            if mdpowers_dir.is_dir():
                # Find all vocabulary.*.json files in this .mdpowers/
                vocab_files = sorted(mdpowers_dir.glob("vocabulary.*.json"))
                overlay_files.extend(vocab_files)

            # Stop walking if we hit .git or root
            if (current / ".git").is_dir() or current == current.parent:
                break
            current = current.parent

    # Load overlays in order (deeper levels loaded last, so they win on conflicts)
    for overlay_file in overlay_files:
        try:
            overlay_data = json.loads(overlay_file.read_text())
            overlay_flat = _flatten_vocab_data(overlay_data)
            merged.update(overlay_flat)
            meta["overlay"] = str(overlay_file)
            meta["overlay_path"] = str(overlay_file)
            meta["overlay_version"] = (
                overlay_data.get("_meta", {}).get("updated", "unknown")
            )
        except json.JSONDecodeError as e:
            raise VocabularyError(f"Malformed overlay vocabulary JSON in {overlay_file}: {e}")

    return merged, meta


# ---------------------------------------------------------------------------
# Whisper priming and post-correction
# ---------------------------------------------------------------------------


def apply_vocabulary(
    text: str, vocab: dict[str, list[str]]
) -> tuple[str, list[tuple[str, str]]]:
    """Post-correct transcript using vocabulary via substring replacement.

    Strategy:
    - Find all vocabulary entries in text (longer variants first to avoid partial matches)
    - Use word boundaries (\\b) for case-insensitive matching
    - Preserve original case on replacement via reversed finditer
    - Only log corrections where the matched text differs from the canonical form
      (filters no-ops where whisperx already got it right)

    Args:
        text: Transcript text to correct.
        vocab: Flattened vocabulary dict where keys are terms/mistakes and
               values are lists of canonical forms.

    Returns:
        Tuple of (corrected_text, corrections) where corrections is a list of
        (matched_text, canonical_form) tuples for genuine changes only.
        No-op replacements (matched == canonical) are excluded.
    """
    if not vocab or not text:
        return text, []

    corrections: list[tuple[str, str]] = []

    # Sort by length descending to handle longer variants first
    sorted_keys = sorted(vocab.keys(), key=len, reverse=True)

    for key in sorted_keys:
        # Build regex pattern with word boundaries
        # Escape special regex chars, then add word boundaries
        escaped_key = re.escape(key)
        pattern = r"\b" + escaped_key + r"\b"

        # Find all matches (case-insensitive)
        matches = list(re.finditer(pattern, text, re.IGNORECASE))
        if not matches:
            continue

        # Replace in reverse order to preserve positions
        canonical = vocab[key][0]  # First entry is the canonical form
        for match in reversed(matches):
            start, end = match.span()
            original_text = text[start:end]

            # Preserve case pattern of the original matched text
            # ALL CAPS -> replace with CANONICAL in all caps
            # First letter upper -> replace with CANONICAL in title case
            # Otherwise -> use canonical as-is (likely in its natural case)
            if original_text.isupper() and len(original_text) > 1:
                replacement = canonical.upper()
            elif original_text[0].isupper():
                replacement = canonical[0].upper() + canonical[1:]
            else:
                # For lowercase matches, use canonical as-is
                # (it should be in its proper form from the vocabulary)
                replacement = canonical

            # Only record and apply if something actually changed
            if original_text != replacement:
                corrections.append((original_text, replacement))
                text = text[:start] + replacement + text[end:]

    return text, corrections


def build_whisper_prompt(
    vocab: dict[str, list[str]], token_budget: int = 180
) -> str:
    """Build a Whisper prompt from vocabulary, capped at token budget.

    Strategy:
    - Extract all unique canonical terms (first entry of each vocab value)
    - Sort by length descending
    - Add comma-separated terms until token budget is reached
    - Token count estimated as (len(word) / 4) per word (rough approximation)

    Args:
        vocab: Flattened vocabulary dict.
        token_budget: Maximum tokens for the prompt (default 180).

    Returns:
        Comma-separated string of terms suitable for Whisper API hint.
    """
    if not vocab:
        return ""

    # Extract unique canonical terms
    canonical_terms = set()
    for variants in vocab.values():
        if variants:
            canonical_terms.add(variants[0])

    # Sort by length (longer terms first) to maximize information density
    sorted_terms = sorted(canonical_terms, key=len, reverse=True)

    # Add terms until we hit the token budget
    prompt_terms = []
    current_tokens = 0
    for term in sorted_terms:
        # Rough token estimate: ~4 chars per token
        term_tokens = max(1, len(term) // 4)
        # Account for comma separator
        if prompt_terms:
            term_tokens += 1

        if current_tokens + term_tokens > token_budget:
            break

        prompt_terms.append(term)
        current_tokens += term_tokens

    return ",".join(prompt_terms)


# ---------------------------------------------------------------------------
# Candidate discovery (segments -> unusual words)
# ---------------------------------------------------------------------------


def _load_english_dictionary() -> Optional[set]:
    """Load NLTK words corpus, with auto-download if not available.

    Returns:
        Set of English words, or None if NLTK not available or download fails.
    """
    try:
        import nltk

        # Try to load corpus
        try:
            words = set(nltk.corpus.words.words())
            return words
        except LookupError:
            # Auto-download if missing
            nltk.download("words", quiet=True)
            words = set(nltk.corpus.words.words())
            return words
    except Exception:
        return None


def _in_english_dict(word: str, english_dict: set) -> bool:
    """Check if a word is in the English dictionary using suffix stripping.

    Tries the word as-is, then applies suffix stripping for fuzzy match
    (handling -ed, -ing, -s, etc.).

    Args:
        word: Word to check.
        english_dict: Set of English words.

    Returns:
        True if word or a stripped variant is in the dictionary.
    """
    if not english_dict:
        return False

    word_lower = word.lower()
    if word_lower in english_dict:
        return True

    # Suffix stripping for fuzzy match
    suffixes = [
        "ed", "ing", "s", "es", "tion", "sion", "ment", "ness", "ful", "less",
        "ous", "ious", "al", "ial", "able", "ible", "er", "est", "ly", "ity",
    ]
    for suffix in suffixes:
        if word_lower.endswith(suffix) and len(word_lower) > len(suffix) + 2:
            stripped = word_lower[: -len(suffix)]
            if stripped in english_dict:
                return True

    return False


def find_vocabulary_candidates(
    segments: list[dict], known_vocab: dict[str, list[str]]
) -> dict:
    """Discover vocabulary candidates from transcript segments.

    Three categories:
    1. acronyms: All-caps words (2+ chars) not in English dict, not in known vocab
    2. proper_nouns: Title-cased words (not sentence-initial), not in English dict, not known
    3. unusual: Words not in English dict or known vocab, low-signal check applied

    Also computes low_signal_unusual: set of words filtered by heuristics.

    Args:
        segments: List of segment dicts with "words" list (each word has "word" key).
        known_vocab: Flattened vocabulary dict (to exclude already-known terms).

    Returns:
        Dict with keys: acronyms, proper_nouns, unusual, low_signal_unusual
        Each is a dict mapping term -> {count: int, first_context: str}
    """
    english_dict = _load_english_dictionary()

    # Extract all words from segments
    word_list = []
    for segment in segments:
        if "words" in segment and isinstance(segment["words"], list):
            for word_entry in segment["words"]:
                if isinstance(word_entry, dict) and "word" in word_entry:
                    word_list.append(word_entry["word"])

    candidates = {
        "acronyms": {},
        "proper_nouns": {},
        "unusual": {},
        "low_signal_unusual": set(),
    }

    # Build known terms set for quick lookup
    known_terms = set(known_vocab.keys())

    for i, word in enumerate(word_list):
        word_clean = word.strip()
        if not word_clean or len(word_clean) < 2:
            continue

        # Skip if already in known vocab
        if word_clean.lower() in known_terms or word_clean in known_terms:
            continue

        # Context: nearby words for documentation
        context_start = max(0, i - 2)
        context_end = min(len(word_list), i + 3)
        context = " ".join(word_list[context_start:context_end])

        # Category 1: Acronyms (all-caps, 2+ chars)
        if word_clean.isupper() and len(word_clean) >= 2:
            if word_clean not in candidates["acronyms"]:
                candidates["acronyms"][word_clean] = {
                    "count": 0,
                    "first_context": context,
                }
            candidates["acronyms"][word_clean]["count"] += 1
            continue

        # Category 2: Proper nouns (title-cased, not at sentence start)
        if word_clean[0].isupper() and i > 0:
            prev_word = word_list[i - 1].strip().lower()
            if prev_word not in (".", "!", "?", ""):  # Not sentence-initial
                if word_clean not in candidates["proper_nouns"]:
                    candidates["proper_nouns"][word_clean] = {
                        "count": 0,
                        "first_context": context,
                    }
                candidates["proper_nouns"][word_clean]["count"] += 1
                continue

        # Category 3: Unusual words (not in English dict)
        if not _in_english_dict(word_clean, english_dict):
            if word_clean not in candidates["unusual"]:
                candidates["unusual"][word_clean] = {
                    "count": 0,
                    "first_context": context,
                }
            candidates["unusual"][word_clean]["count"] += 1

            # Low-signal heuristics: skip very short, numbers, single-char repeats, etc.
            is_low_signal = (
                len(word_clean) < 3
                or word_clean.isdigit()
                or all(c == word_clean[0] for c in word_clean)
                or any(c in word_clean for c in "0123456789")
            )
            if not is_low_signal:
                candidates["low_signal_unusual"].add(word_clean)

    return candidates


# ---------------------------------------------------------------------------
# GPT assessment and review file writing
# ---------------------------------------------------------------------------


def gpt_assess_candidates(client, candidates: dict, title: str) -> str:
    """Get GPT-4o-mini assessment of vocabulary candidates.

    Calls OpenAI API to evaluate and filter candidates for vocabulary addition.

    Args:
        client: OpenAI client instance.
        candidates: Dict from find_vocabulary_candidates.
        title: Title/name of the source (for context in prompt).

    Returns:
        GPT response text with assessment and recommendations.

    Raises:
        VocabularyError: If API call fails.
    """
    # Build candidate summary
    summary = []
    for category in ["acronyms", "proper_nouns", "unusual"]:
        items = candidates.get(category, {})
        if items:
            summary.append(f"\n{category.upper()}:")
            for term, data in sorted(items.items(), key=lambda x: -x[1]["count"])[:20]:
                summary.append(f"  - {term} (count: {data['count']})")

    prompt = f"""Review the following vocabulary candidates from a transcript titled "{title}".
For each term, indicate whether it should be added to the vocabulary set, and suggest appropriate categorization.

Candidates:
{"".join(summary)}

Provide a concise assessment with recommendations for each term."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise VocabularyError(f"GPT assessment failed: {e}")


def write_vocabulary_review(
    out_path: Path,
    title: str,
    candidates: dict,
    gpt_notes: str,
    corrections_applied: int = 0,
) -> None:
    """Write vocabulary review file for human curation.

    Creates a markdown file documenting candidates, GPT assessment, and
    instructions for promotion workflow.

    Args:
        out_path: Path to write review file.
        title: Title of the source transcript.
        candidates: Dict from find_vocabulary_candidates.
        gpt_notes: Assessment from gpt_assess_candidates.
        corrections_applied: Count of corrections already applied to transcript.
    """
    review_text = f"""# Vocabulary Review: {title}

**Generated:** {datetime.now().isoformat()}
**Corrections Already Applied:** {corrections_applied}

## GPT Assessment

{gpt_notes}

## Candidate Summary

### Acronyms
{_format_candidates_section(candidates.get("acronyms", {}))}

### Proper Nouns
{_format_candidates_section(candidates.get("proper_nouns", {}))}

### Unusual Words
{_format_candidates_section(candidates.get("unusual", {}))}

## Next Steps

To add terms to your vocabulary:

1. Review the candidates and GPT notes above
2. Choose the terms you want to add
3. Use the `promote_to_master()` or `add_term_to_vocab()` functions to add them to your vocabulary

Vocabulary is stored in the active vocabulary set (master + overlay).
Update `_meta.updated` to today's date after making changes.

## Instructions for Promotion

**Via `promote_to_master(term, overlay_path, master_path)`:**
- Moves a term from overlay vocabulary to master
- Only works if term exists in overlay and not already in master

**Via `add_term_to_vocab(vocab_path, category, term, mistranscriptions, context)`:**
- Adds a new term to any vocabulary file
- Specify category, common mistranscriptions, and optional context note

"""

    out_path.write_text(review_text)


def _format_candidates_section(candidates: dict) -> str:
    """Format a candidates dict for the review file."""
    if not candidates:
        return "(none)\n"

    lines = []
    for term, data in sorted(candidates.items(), key=lambda x: -x[1]["count"]):
        lines.append(f"- **{term}** (count: {data['count']})")
        lines.append(f"  - Context: {data['first_context']}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Promotion and term addition
# ---------------------------------------------------------------------------


def promote_to_master(term: str, overlay_path: Path, master_path: Path) -> dict:
    """Promote a term from overlay vocabulary to master.

    Workflow:
    1. Load overlay JSON, find term in any category
    2. If not found, raise VocabularyError
    3. Load master JSON, check for conflicts
    4. If already exists in master, raise VocabularyError with conflict_payload
    5. Copy entry verbatim to master under same category
    6. Update master _meta.updated to today's ISO date
    7. Write master file, return promoted entry

    Args:
        term: The term to promote (must exist in overlay).
        overlay_path: Path to overlay vocabulary file.
        master_path: Path to master vocabulary file.

    Returns:
        The promoted entry dict.

    Raises:
        VocabularyError: If term not found in overlay, or conflict detected.
    """
    # Load overlay
    try:
        overlay_data = json.loads(overlay_path.read_text())
    except json.JSONDecodeError as e:
        raise VocabularyError(f"Malformed overlay vocabulary JSON: {e}")

    # Find term in overlay
    overlay_category = None
    overlay_entry = None
    for category, entries in overlay_data.items():
        if category == "_meta":
            continue
        if isinstance(entries, dict) and term in entries:
            overlay_category = category
            overlay_entry = entries[term]
            break

    if not overlay_entry:
        raise VocabularyError(f"Term '{term}' not found in overlay vocabulary")

    # Load master
    try:
        master_data = json.loads(master_path.read_text())
    except json.JSONDecodeError as e:
        raise VocabularyError(f"Malformed master vocabulary JSON: {e}")

    # Check for conflicts
    for category, entries in master_data.items():
        if category == "_meta":
            continue
        if isinstance(entries, dict) and term in entries:
            raise VocabularyError(
                f"Term '{term}' already exists in master vocabulary",
                conflict_payload={
                    "term": term,
                    "overlay_entry": overlay_entry,
                    "master_entry": entries[term],
                    "overlay_category": overlay_category,
                    "master_category": category,
                },
            )

    # Copy entry to master under same category
    if overlay_category not in master_data:
        master_data[overlay_category] = {}
    master_data[overlay_category][term] = overlay_entry

    # Update _meta
    if "_meta" not in master_data:
        master_data["_meta"] = {}
    master_data["_meta"]["updated"] = datetime.now().strftime("%Y-%m-%d")

    # Write master
    master_path.write_text(json.dumps(master_data, indent=2))

    return overlay_entry


def add_term_to_vocab(
    vocab_path: Path, category: str, term: str, mistranscriptions: list[str], context: str = ""
) -> None:
    """Add a new term to any vocabulary file.

    Workflow:
    1. Load vocabulary JSON
    2. Create category if it doesn't exist
    3. Add entry as {term: {"mistranscriptions": [...], "context": context}}
    4. Update _meta.updated to today's ISO date
    5. Write file back with indent=2

    Args:
        vocab_path: Path to vocabulary file.
        category: Category to add term to (created if missing).
        term: The term to add.
        mistranscriptions: List of known mistranscription variants.
        context: Optional note about when/where this term appears.

    Raises:
        VocabularyError: If vocabulary file is malformed.
    """
    try:
        vocab_data = json.loads(vocab_path.read_text())
    except json.JSONDecodeError as e:
        raise VocabularyError(f"Malformed vocabulary JSON in {vocab_path}: {e}")

    # Create category if missing
    if category not in vocab_data:
        vocab_data[category] = {}

    # Add entry
    vocab_data[category][term] = {
        "mistranscriptions": mistranscriptions,
        "context": context,
    }

    # Update _meta
    if "_meta" not in vocab_data:
        vocab_data["_meta"] = {}
    vocab_data["_meta"]["updated"] = datetime.now().strftime("%Y-%m-%d")

    # Write file
    vocab_path.write_text(json.dumps(vocab_data, indent=2))


# ---------------------------------------------------------------------------
# Import guard for os (needed for env var access)
# ---------------------------------------------------------------------------

import os
