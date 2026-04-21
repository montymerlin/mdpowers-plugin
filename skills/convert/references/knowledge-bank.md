---
title: "PDF-to-Markdown Conversion Knowledge Bank"
date: 2026-03-26
tags: #research #pdf #conversion #docling #knowledge-bank
---

# PDF-to-Markdown Conversion Knowledge Bank

Lessons learned from converting 16 reference PDFs in the Bridging Worlds research commons using Docling v2.69.1 on macOS (Apple Silicon).

## Tool

**Docling** (`pip install docling`) — IBM-backed, 57k GitHub stars, MIT license.

**Command template:**
```bash
docling "input.pdf" --to md --image-export-mode referenced --output "output_dir/"
```

Always use `--image-export-mode referenced` to extract images as separate PNGs rather than embedding base64 data inline. The `embedded` default bloats markdown files 5-10x.

**Post-processing:** `tools/pdf_postprocess.py` — handles image reorganization, HTML entity decoding, Unicode ligature fixes, academic paper cleanup, and artifact removal.

## Known Issues and Fixes

### 1. Base64 Image Embedding (Critical)
- **Problem:** Default `--image-export-mode embedded` encodes every image as base64 inline. A 1.1MB PDF essay produced a 505KB markdown file; with `referenced` mode it was 94KB.
- **Fix:** Always use `--image-export-mode referenced`.
- **Impact:** 5-10x file size reduction. Essential for search indexing (QMD would tokenize the base64 strings wastefully).

### 2. Nested Image Output Paths
- **Problem:** Docling creates deeply nested `_artifacts/` directories mirroring the full input path (e.g. `projects/<project>/reference/md/projects/<project>/...`).
- **Fix:** Post-processor moves images to a flat `images/` folder with shortened, clean filenames and updates markdown references to relative paths.

### 3. Two-Column Academic Paper Layout → Table
- **Problem:** Academic papers with two-column layouts get parsed as tables with duplicated content in both columns (each column becomes a table cell with identical text).
- **Fix:** Post-processor detects duplicated-column tables and extracts the content as plain paragraphs.
- **Severity:** High for Frontiers-style papers. Clean reports (WEF, independent essays) are unaffected.

### 4. Line-Numbered Manuscripts → Table with Numbers
- **Problem:** Academic papers with manuscript line numbers (common in Frontiers, Nature, etc.) get parsed as tables where the first column contains line numbers (1, 2, 3...) and content is in subsequent columns.
- **Fix:** Post-processor detects rows where >50% have numeric first cells and extracts content from remaining columns.
- **Severity:** Medium. Affects the abstract/metadata section most; body text is usually cleaner.

### 5. HTML Entity Encoding
- **Problem:** `&amp;` appears instead of `&`, `&lt;` instead of `<`, etc.
- **Fix:** `html.unescape()` in post-processor.
- **Severity:** Low. Easy automatic fix.

### 6. Unicode Ligature References
- **Problem:** Some PDFs produce `/uniFB01` instead of "fi", `/uniFB02` instead of "fl", etc. Common in Springer/Nature papers.
- **Fix:** Post-processor maps known ligature codes to characters and uses a generic `/uniXXXX` → `chr(0xXXXX)` fallback.
- **Severity:** Low-medium. Makes text unreadable if unfixed ("/uniFB01nance" instead of "finance").

### 7. Publisher Metadata Artifacts
- **Problem:** Springer papers include `1234567890():,;` as a metadata artifact on line 1.
- **Fix:** Post-processor strips this pattern.
- **Severity:** Low. Cosmetic.

### 8. Page Break Artifacts
- **Problem:** Lone periods (`.`) on their own line mark page breaks.
- **Fix:** Post-processor removes isolated periods.
- **Severity:** Low. Cosmetic.

### 9. Excessive Blank Lines
- **Problem:** Page breaks and layout transitions produce runs of 10-40+ blank lines.
- **Fix:** Post-processor collapses 3+ consecutive blank lines to a single blank line.
- **Severity:** Low. Cosmetic but wastes tokens in context windows.

### 10. Spaced-Out Title Text
- **Problem:** PDF titles using letter-spaced typography produce output like `I N S I G H T   R E P O R T`.
- **Fix:** Not automatically fixed (would need OCR-level reconstruction). Doesn't affect searchability since the words are present.
- **Severity:** Very low. Cosmetic only.

### 11. Flat Heading Hierarchy (All H2)
- **Problem:** Docling outputs every heading as `##` (H2) regardless of the actual hierarchy in the PDF. Document titles, chapter headings, sub-sections, and sub-sub-sections all get the same level.
- **Fix:** Post-processor `fix_heading_hierarchy()` infers the correct level using multiple signals:
  - First heading in the document → H1 (title)
  - CHAPTER/PART headings → H2
  - Structural keywords (Introduction, Conclusion, References, etc.) → H2
  - Numbered sections: depth from number (1 → H2, 1.1 → H3, 1.1.1 → H4)
  - ALL CAPS headings → H2
  - BOX/EXHIBIT/FIGURE labels → H4
  - Default remaining headings → H3
- **Severity:** High for document navigation and search chunking.

### 12. False Headings (Paragraphs as Headings)
- **Problem:** Sentences that were styled as bold/large in the PDF get marked as headings. Quotes, long descriptive sentences, and bullet-point-style text become headings.
- **Fix:** Post-processor demotes to bold paragraphs when: text ends with a period and is >60 chars, text starts with a quote mark and is >40 chars, text is >120 chars, or text is a bullet marker (·, •, -, *).
- **Severity:** Medium. Pollutes heading structure and confuses search chunking.

### 13. Unresolved Font Glyph IDs
- **Problem:** Some PDFs (especially those using custom fonts or OpenType features) produce `/gidXXXXX` references instead of actual characters. Grassroots Economics was 99% glyph IDs.
- **Fix:** Post-processor `fix_glyph_ids()` strips all `/gidXXXXX` patterns and cleans up empty headings and excess spaces left behind. Also runs `_clean_glyph_aftermath()` to remove artifacts left behind: empty tables, lone escape chars, bare quotes/dashes, orphaned numbered lists, duplicate lines, and printer marks.
- **Severity:** Critical when present. The entire document is unreadable without this fix.

### 14. Custom Font — Text Layer Has Glyph IDs Instead of Characters
- **Problem:** Some books (e.g., Grassroots Economics) use a custom embedded font where the glyph-to-character mapping is not standard. Standard text extraction produces `/gidXXXXX` strings instead of readable text.
- **Fix:** Re-convert with `--force-ocr`. This bypasses the broken text layer entirely and reads the rendered page images via OCR. Grassroots Economics went from 355 lines (skeleton) to 1,707 lines (full book) with this approach. The OCR output is clean and needs only minimal post-processing (3.7% reduction).
- **Severity:** Critical when present, but fully recoverable with `--force-ocr`. The verification tool (`tools/pdf_verify.py`) catches this via low prose density and glyph ID artifact detection.

### 15. Spaced Ligatures (fi, fl as space-separated characters)
- **Problem:** Frontiers/Springer papers render ligatures as `fi nance`, `ef fi cacy`, `con fl ict` — the ligature characters are replaced with the individual letters plus a space.
- **Fix:** Post-processor `fix_spaced_ligatures()` uses regex to rejoin `fi`/`fl`/`ff` fragments mid-word (`(?<=[a-zA-Z]) fi (?=[a-z])` → `fi`) and at word-start (`(?<=\s)fi (?=[a-z])` → `fi`).
- **Severity:** Medium. Affects readability and search indexing (searching "finance" won't match "fi nance").
- **Files affected:** `digital commons & DAOs.md`, `Ecological Money and Finance.md`.

### 16. Embedded Watermark Text
- **Problem:** Draft/pre-release PDFs may contain invisible watermark text (e.g., "Confidential Do Not Share everdred") that Docling extracts as visible text. The watermark text may appear standalone or concatenated mid-word (`highereverdred`, `contributioneverdred`).
- **Fix:** Post-processor `strip_watermarks()` removes known watermark patterns. Also requires manual review for concatenated instances (where the watermark breaks the word it's attached to).
- **Severity:** Medium. Watermark text pollutes the content and breaks words. Manual fix needed for mid-word concatenation.
- **Files affected:** `Abundance Networks Pre-Release DO NOT SHARE.md`.

### 17. Duplicated End-Matter (Two-Column Extraction)
- **Problem:** Academic papers with two-column layouts may have their back-matter (Conflict of Interest, Funding, Acknowledgements) extracted with each sentence duplicated — once from each column.
- **Fix:** Post-processor `fix_duplicate_lines()` removes consecutive duplicate lines >30 chars. For partially duplicated lines (same text merged into a single line), manual deduplication is needed.
- **Severity:** Low-medium. Affects back-matter readability.
- **Files affected:** `Kate Bennett - The ReFi Movement...md`.

### 18. Over-Promoted Definition Headings
- **Problem:** OCR-converted books may promote numbered definition items (e.g., "1. Seeding:", "2. Swapping:") and bullet-style terms (e.g., "• Hyphae:") to H2/H3 headings when they should be H4 or bold inline text.
- **Fix:** Manual or script-based demotion. Numbered items: `## 1. X:` → `#### 1. X:`. Bullet items: `### • X:` → `**• X:**`.
- **Severity:** Medium. Pollutes heading hierarchy and confuses document navigation.
- **Files affected:** `Grassroots Economics.md`.

### 19. Transitional Sentences as Headings
- **Problem:** Sentences that serve as transitions between sections (e.g., "This is what the next chapter begins to explore.") get promoted to headings in the conversion.
- **Fix:** Manual demotion to body text. The `fix_heading_hierarchy()` function catches some of these via the false-heading heuristic (ends with period, >60 chars), but shorter transitional sentences may slip through.
- **Severity:** Low. Cosmetic but affects reading flow.
- **Files affected:** `Reimagining Nature Finance Essay Sept 2025.md`.

## Quality Assessment by Document Type

| Document Type | Quality | Notes |
|---|---|---|
| Clean reports/essays | Excellent | Headings, paragraphs, footnotes all preserved. Minor artifacts only. |
| Books (Ethereum Localism, Abundance Networks) | Good | Table of contents may be messy, but body text is clean. |
| Books with custom fonts (Grassroots Economics) | Good (with --force-ocr) | Standard extraction fails (glyph IDs). Re-convert with `--force-ocr` to recover full text via OCR. |
| WEF/institutional reports | Good | Complex layouts handled well. Tables preserved. Images extracted. |
| Academic papers (Frontiers, Springer) | Fair | Two-column and line-number issues. Post-processor fixes most. Some residual noise in abstract sections. |
| Papers with equations/math | Not tested | Docling supports LaTeX but we didn't have math-heavy PDFs. |

## Statistics (Bridging Worlds Batch)

- 16 PDFs converted (15 standard, 1 with --force-ocr)
- ~2,200 chunks indexed by QMD across 71 documents (4 collections)
- 410+ images extracted
- Conversion time: ~10 minutes standard on M-series Mac; ~2 minutes per file with --force-ocr

## Conversion Workflow

The standard workflow for converting new PDFs:

```
1. CONVERT        docling "file.pdf" --to md --image-export-mode referenced --output reference/md/
2. POST-PROCESS   python tools/pdf_postprocess.py reference/md/file.md
3. AUTO-VERIFY    python tools/pdf_verify.py reference/md/file.md --reference-dir reference/
4. LLM REVIEW     Read and assess the converted file (see review protocol below)
5. FIX            Address any issues found. Re-convert with --force-ocr if needed.
6. INDEX          Update QMD collection and re-embed
```

### Step 3: Auto-Verify (mechanical)

`pdf_verify.py` is a fast, free first pass that catches surface-level issues: glyph ID remnants, broken image references, base64 embedding, flat heading hierarchy, orphaned list items. It also flags when `--force-ocr` may be needed. Run it automatically; it takes <1 second.

### Step 4: LLM Review (quality gate)

After post-processing, the agent reads the converted file and assesses it holistically. This is the real quality gate — it catches issues no mechanical checker can.

**Review protocol — read these sections of each converted file:**
- **First ~80 lines**: Does the document start with a clear title? Is there coherent introductory prose? Or just fragments and image references?
- **Middle section (~40% through)**: Is body text flowing naturally? Are paragraphs complete? Do headings make structural sense?
- **Last ~60 lines**: Does the document end properly (conclusion, references, appendix)? Or does it trail off with artifacts?
- **Any area flagged by pdf_verify.py**

**What to assess:**
- **Readability**: Does the prose read naturally? Are there garbled sentences, missing words, or mid-sentence truncations?
- **Heading structure**: Do headings follow a logical hierarchy? Are terms like "### • Hyphae:" better as bold inline text than headings? Are there paragraph-length "headings" that should be body text?
- **Tables**: Do they make sense in context? Or are they artifacts from two-column layout parsing?
- **Completeness**: Does the content match what you'd expect from the document type? A 200-page book should have substantial prose, not just headings and footnotes.
- **Formatting**: Are footnotes properly placed? Are blockquotes used appropriately? Are lists well-formed?
- **Images**: Are references pointing to real files? Do image placements make sense in the document flow?

**Decision tree after review:**
- Content looks good → proceed to indexing
- Minor formatting issues → fix in-place (edit the markdown directly)
- Major content loss (fragments, glyph artifacts, missing body text) → re-convert with `--force-ocr`, re-run post-processor, re-review
- Document-specific issue → add to the Known Issues section above and update `pdf_postprocess.py` if automatable

### When to use `--force-ocr`

Only when standard extraction produces garbled text (glyph IDs, empty body with only headings/footnotes). Most PDFs — even heavily designed ones — extract fine with standard mode. Force-OCR is 2-3x slower but reads the rendered page images via OCR, bypassing font encoding issues.

### Key learnings

- The PDF-to-markdown size ratio is unreliable for detecting content loss. Image-heavy reports (WEF, design-focused) routinely have 1-5% text-to-PDF ratios and that's normal.
- The real signals for content loss are: glyph ID artifacts, low prose density, low word count, and — most reliably — an LLM reading the output and noticing it doesn't make sense.
- Mechanical verification and LLM review complement each other: the script catches what's easy to miss when skimming (a single broken image ref buried in 2000 lines), while the LLM catches what no regex can (a heading that should be a paragraph, a section that reads like garbled fragments).

## Future Improvements

1. **VLM pipeline for tough PDFs:** Docling has `--pipeline vlm` mode using vision-language models. Could improve academic paper parsing. Worth testing if we add more Frontiers/Nature papers.
2. **Equation support:** If math-heavy PDFs are added, test Docling's LaTeX output quality.
3. **Incremental conversion:** When new PDFs are added to `reference/`, only convert new ones. The post-processor can be run in batch mode on a directory.
4. **YAML frontmatter:** Could add frontmatter (title, author, date, source) to each converted file for better QMD context. Would need a mapping file or manual addition.
