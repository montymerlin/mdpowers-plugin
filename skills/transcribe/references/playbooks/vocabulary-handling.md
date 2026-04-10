# Vocabulary Handling Playbook

Complete guide to vocabulary discovery, merging, priming, and post-correction across both transcription pathways.

## Discovery Cascade

When the transcription skill starts, vocabulary sources are discovered and merged in a strict priority order. The **first available** source at each level wins; deeper sources are skipped.

**The six-step ordered discovery cascade:**

1. **Empty/merged dictionary check** — If no prior vocabularies merged this session, start fresh (empty dict). If merging happened, use the merged result from step 6 as baseline.

2. **$MDPOWERS_VOCAB environment variable** — Check if `$MDPOWERS_VOCAB` is set to a file path. If set and file exists, load that vocabulary JSON as the master dictionary. If set but file missing, warn and continue. If unset, skip to step 3.

3. **XDG master vocabulary** — Look for vocabulary file at `~/.config/mdpowers/vocabularies/master.json` (XDG Config Home standard). This is the user's global default vocabulary. If present, load it. If missing, skip.

4. **Walk-up directory overlays** — Starting from current working directory, walk up to root. At each level, check for `.mdpowers/vocabularies/` directory. Load all JSON files found, **deepest (closest to cwd) wins** for conflicting keys. This allows project-specific vocabularies to override global defaults.

5. **Explicit --vocab-overlay flag** — If user provided `--vocab-overlay path/to/vocab.json` on command line, load that file and merge into the current vocabulary. This source has the highest priority — it overrides all previous sources.

6. **Final flattened dictionary** — Merge all discovered vocabularies using the rules in "Merge Semantics" below. Result is a single flat dictionary used for priming and correction.

**Example discovery walk:**
```
Start at: /home/user/projects/podcast-transcripts
  Level 1: /home/user/projects/podcast-transcripts/.mdpowers/vocabularies/ (if exists, load all JSONs)
  Level 2: /home/user/projects/.mdpowers/vocabularies/ (if exists, load all JSONs)
  Level 3: /home/user/.mdpowers/vocabularies/ (if exists, load all JSONs)
  Level 4: /.mdpowers/vocabularies/ (if exists, root-level — rare)
  Then: Check $MDPOWERS_VOCAB (overrides all walk-ups)
  Then: Check ~/.config/mdpowers/vocabularies/master.json
  Finally: Apply explicit --vocab-overlay (highest priority)
Result: Flattened merged vocabulary
```

## Scope Selection

When multiple vocabulary overlay files exist in a directory (e.g., `.mdpowers/vocabularies/`), scope determines which is primary:

1. **Explicit --vocab-overlay path** — If user specified a file, use only that file (no merging with directory siblings).

2. **_meta.scope field match** — If a vocabulary JSON contains `"_meta": {"scope": "podcast"}` and the transcription is tagged with scope "podcast", prefer that vocabulary.

3. **Directory name as scope hint** — If directory is `.mdpowers/vocabularies-finance/`, treat "finance" as implied scope. Load all JSONs in that directory.

4. **Alphabetical with warning** — If no scope specified and multiple vocabularies in same directory, load all files alphabetically. Warn user: "Multiple vocabularies found; merged in order: vocab_a.json, vocab_b.json. Specify --vocab-overlay to override."

**Anti-pattern:** Do not attempt fuzzy scope matching. Scope must be explicit in _meta or file path; ambiguous scopes are an error.

## Merge Semantics

When multiple vocabularies are discovered, they are **merged** (not unioned). The rule is simple:

**Overlay REPLACES master** — If a key exists in both master and overlay, the overlay value wins. Keys unique to master are kept.

**Example:**
```json
// master.json
{
  "crypto": "Cryptocurrency",
  "aum": "Assets Under Management",
  "defi": "Decentralized Finance"
}

// overlay.json
{
  "crypto": "Crypto-Currency",
  "nft": "Non-Fungible Token"
}

// Merged result:
{
  "crypto": "Crypto-Currency",    // Overlay value
  "aum": "Assets Under Management", // Master value (unique)
  "defi": "Decentralized Finance",  // Master value (unique)
  "nft": "Non-Fungible Token"      // Overlay value (unique)
}
```

**Nested merging:** If both vocabularies contain objects with nested definitions (rare), merge recursively at one level only. Do not deep-merge beyond first level of nesting.

## Priming (Pathway 2 Only)

Priming is the process of **preparing the vocabulary to guide Whisper during transcription** (P2-whisperx-local). P1 does not use priming because it uses existing captions.

**Priming steps:**

1. **Flatten to list** — Convert merged vocabulary dictionary to a simple list of values (ignoring keys). Example: `["Cryptocurrency", "Assets Under Management", "Decentralized Finance", ...]`

2. **Priority sort** — Sort the list by priority:
   - Rank 1 (highest): Confused terms (terms you've corrected before; marked with `"confused": true` in metadata)
   - Rank 2: Orgs and people (proper nouns)
   - Rank 3: Concepts and domains
   - Rank 4 (lowest): Acronyms
   
   Within each rank, preserve insertion order (don't re-sort alphabetically).

3. **Cap at 180 tokens** — Estimate token count for final list (OpenAI tokenizer: ~1.3 chars per token). If > 180 tokens, truncate from rank 4 (acronyms) upward. Warn user if truncated: "Vocabulary vocabulary truncated to 180 tokens; {N} lowest-priority terms omitted."

4. **Comma-separated format** — Join list as comma-separated string: `"Cryptocurrency, Assets Under Management, Decentralized Finance, ..."`

5. **Pass to Whisper prompt** — Prepend to Whisper's system prompt (if model supports prompting). This increases the likelihood Whisper will recognize and correctly transcribe these terms.

## Post-Correction (Both Pathways)

Post-hoc correction is applied **after transcription completes**, using substring replacement. This fixes mistranscriptions that the model should have caught but didn't.

**Correction algorithm:**

1. **Iterate transcript line by line** — For each line of transcribed text.

2. **Longest-variant-first** — For each term in the vocabulary, check the longest variant first (if multiple spellings exist in vocabulary). This prevents partial replacement.

3. **Case-insensitive word-boundary match** — Use regex `\b{term}\b` with IGNORECASE flag. Boundary check prevents replacing "credit" inside "accreditation". Example:
   ```python
   import re
   term = "Assets Under Management"
   pattern = re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
   ```

4. **Preserve original case** — When replacing, detect case of original text and apply to replacement. Examples:
   - Original: `"assets under management"` → Replace with: `"Assets Under Management"` (exact match)
   - Original: `"ASSETS UNDER MANAGEMENT"` → Replace with: `"ASSETS UNDER MANAGEMENT"` (all caps preserved)
   - Original: `"Assets under management"` → Replace with: `"Assets Under Management"` (title case preserved)

5. **Log corrections** — For each replacement made, log the before/after pair and vocabulary source. Include in output file metadata: `vocab_corrections: [{original: "...", corrected: "...", source: "vocab_overlay"}]` (optional, for reproducibility).

**Example post-correction flow:**
```
Transcript line: "The defI protocol uses nft assets for collateral."

Vocabulary: {"defi": "DeFi", "nft": "NFT"}

Step 1: Check "DeFi" (key: "defi")
  Pattern: \bdefi\b (case-insensitive)
  Match found: "defI"
  Preserve case: Original is mixed case; apply title case → "DeFi"
  Replace: "The DeFi protocol uses nft assets for collateral."

Step 2: Check "NFT" (key: "nft")
  Pattern: \bnft\b (case-insensitive)
  Match found: "nft"
  Preserve case: Original is lowercase; apply lowercase → "NFT" (but all-caps vocab, so use as-is)
  Replace: "The DeFi protocol uses NFT assets for collateral."

Result: "The DeFi protocol uses NFT assets for collateral."
```

## Candidate Discovery

Candidate discovery is the process of identifying which words/terms in the transcript **should be added to the vocabulary** because they were consistently mistranscribed, or are domain-specific and worth encoding for future use.

**Three categories of candidates:**

### Category 1: Acronyms

- **Pattern:** All-caps, length 2–6 characters, not common English words
- **Regex:** `^[A-Z]{2,6}$` (excluding common words: USA, FBI, UK — maintain a stoplist)
- **Example candidates:** REGEN, USDC, IPFS, ReFi
- **Discovery:** Scan transcript for matching patterns. Filter by frequency (appear ≥2 times). Run through GPT-4o-mini to confirm it's not a false positive.

### Category 2: Proper Nouns

- **Pattern:** Title-cased (first letter capital) in middle of sentence (not sentence start)
- **Example candidates:** Gregory Landua, Regen Network, Kolektivo
- **Discovery:** Use NLP (spacy or similar) to identify proper nouns. Or simple heuristic: Title case + appears in ≥2 locations + not at sentence start.

### Category 3: Rare/Unusual Terms

- **Pattern:** Unusual length (≥9 chars), low frequency in NLTK corpus, appears in transcript
- **Example candidates:** "bioregional", "reforestation", "tokenomics"
- **Discovery:** Scan transcript. For each word not in NLTK: check corpus frequency. If frequency = 1 and length ≥9, candidate.

**Candidate assessment:**

Once candidates are discovered, use **GPT-4o-mini** with a structured prompt to assess:
```json
{
  "candidate": "REGEN",
  "assessment": {
    "is_acronym": true,
    "is_proper_noun": false,
    "is_rare_term": false,
    "confidence": 0.95,
    "recommended_canonical": "REGEN",
    "context_examples": ["...REGEN Network...", "...uses REGEN token..."]
  }
}
```

Output is saved to `vocab_reviews/{session_id}_{timestamp}.json` for user review.

## Promotion Workflow

When a candidate term passes assessment and user approves, promote it from candidate → vocabulary.

**Promotion steps:**

1. **Find candidate in overlay file** — Check if candidate already exists in active vocabulary overlay (from step 5 of discovery cascade).

2. **Check master for conflict** — If not in overlay, check if it exists in master vocabulary with a different canonical form. Example:
   - Overlay: empty
   - Master: `{"regen": "Regen Network"}`
   - Candidate: `"REGEN"`
   - Conflict: Should canonical be "Regen Network" or "REGEN"? Show diff to user.

3. **Diff and decide** — If conflict, show user the options:
   - Option A: Add to overlay as new key: `{"regen": "Regen Network", "REGEN": "REGEN"}`
   - Option B: Update master: `{"regen": "REGEN"}`
   - Option C: Don't promote (keep candidate in vocab_reviews/ for later)

4. **Copy or merge** — User chooses. Write to selected vocabulary file (overlay or master).

5. **Ask about overlay removal** — If a term was in both master and a lower-priority overlay (that lost in merge), ask: "This term was in lower-priority overlay; remove from there?" If yes, update that file.

**Promotion confirmation prompt:**
```
Promote candidate "REGEN" → Vocabulary?

Current state:
  Master: (empty)
  Overlay: (none active)

Proposed addition:
  Key: "regen"
  Canonical: "REGEN"
  Context: "REGEN Network", "REGEN token"

Write to: [overlay] / [master] / [skip]?
```

---

## Implementation Notes

- **File formats:** All vocabulary files are JSON. Structure: flat dict `{"mistranscribed": "canonical"}` with optional `"_meta": {"scope": "...", "created": "...", "confused": [...]}` object.
- **Encoding:** UTF-8 for all files.
- **Validation:** On load, validate JSON syntax. If invalid, warn and skip file.
- **Performance:** Priming and post-correction are both O(n*m) where n = transcript lines, m = vocabulary size. For typical vocabularies (100–500 terms), <1 second. Cache compiled regex patterns for repeated use.
- **Reproducibility:** Always log which vocabulary files were used and their discovery order in the output frontmatter.
