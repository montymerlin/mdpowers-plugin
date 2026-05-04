# Recipe catalogue

Seven archetypes for v1. Each recipe is a starting point, not a rail — if a document doesn't cleanly match one of these, pick the closest and adapt (or fall through to `hybrid-novel` and escalate to deep budget).

---

## slide-deck-visual

The Kwaxala case: widescreen PDF or pptx with heavy imagery and diagrams per slide.

**Triggers:**
- File type: PDF or pptx
- Page/slide count: ≤60
- Aspect ratio: widescreen (>1.3:1) or native pptx
- Layout: single-column per page, low text-per-page ratio
- Visual density: high (many diagrams, photos, or illustrations)

**Engine preference:**
1. Built-in `pptx` skill (for native pptx files)
2. Built-in `pdf` skill + pymupdf for page renders (for PDF slide exports)
3. pymupdf direct (fallback)

**Enrichment:** P1, P2, P3, P4, P5, P6

**Output shape:**
```
<deck-slug>.md                    # frontmatter + exec summary + one H2 per slide
<deck-slug>-slides/               # per-slide JPEG renders
  slide-01.jpg
  slide-02.jpg
  ...
```

Each slide section contains: `![](./slides/slide-NN.jpg)` → 2-4 sentence semantic description → structured block (mermaid for flowcharts, table for comparisons) where applicable.

**Required frontmatter fields:** `title`, `source_file`, `source_type`, `recipe: slide-deck-visual`, `extracted_via`, `converted_on`, `quality`, `slides` (count), `deck_type` (pitch | lecture | report | other), `summary`.

**Success criteria:**
- Every slide represented as its own H2 section
- Every slide has image reference + semantic description
- Every flowchart or comparison has structured form (not just image)
- Executive summary section at top compresses deck into 2 paragraphs
- Cross-reference glossary at bottom

**Default budget:** standard

**Image settings:** 144dpi JPEG q82, target <500KB per slide

---

## academic-paper

Published journal articles, working papers, preprints.

**Triggers:**
- File type: PDF
- Layout: often 2-column, but can be 1-column for preprints
- Structural signals: abstract heading, references section, figures with captions
- Metadata: DOI present, author block on first page, journal name visible
- Size: typically 10-40 pages

**Engine preference:** Branches on `math_density` from Probe — full routing rules in `references/environments.md` → "For PDF inputs".

*math_density: high* (theorem/equation markers detected):
1. Built-in `pdf` skill
2. marker (full local host only)
3. docling (full local host only, RAM ≥6GB)
4. pymupdf + post-processing
5. pdftotext + pandoc

*math_density: low* (prose-heavy, minimal notation):
1. pdftotext + pandoc
2. pymupdf + post-processing (if 2-column bleed detected in Verify)
3. Built-in `pdf` skill (only if Verify rejects the above)

**Enrichment:** P3, P4, P5, P6

**Output shape:**
```
<paper-slug>.md                   # frontmatter + body
<paper-slug>-assets/              # only if figures extracted
  fig-01-<caption-slug>.png
  ...
```

Body follows original section order: abstract (inline, also in frontmatter) → introduction → methods → results → discussion → references. Figures promoted to their own sub-sections with captions.

**Required frontmatter fields:** all defaults + `authors` (list), `doi`, `journal`, `year`, `abstract`.

**Success criteria:**
- Abstract populated in frontmatter
- At least one citation in references section parseable
- No 2-column bleed artifacts (text from one column interleaved with the other)
- Figures referenced from body text resolve

**Default budget:** tight-to-standard (tight for short/simple papers, standard for complex ones)

---

## institutional-report

IPBES, FAO, UNDP, think tank reports, NGO publications.

**Triggers:**
- File type: PDF
- Size: 20-300 pages
- Heavy front matter (cover, foreword, acknowledgments, ToC)
- Executive summary section present
- Many figures, tables, and callout boxes
- Publisher name visible (UN agency, NGO, think tank)

**Engine preference:**
1. Built-in `pdf` skill
2. pymupdf with page-range slicing for large reports
3. docling (full local host only, if ≤100 pages)
4. pdftotext + pandoc (last resort)

**Enrichment:** P2, P3, P4, P5, P6

**Output shape:**
```
<report-slug>.md                  # full report in one file if ≤150 pages
<report-slug>-assets/
  fig-01-<caption-slug>.png
  table-01-<caption-slug>.png     # tables extracted as images where complex
  ...
```

For reports >150 pages, consider splitting into sections (treat each Part as its own file, indexed from a root index.md).

Body: full ToC in frontmatter → executive summary verbatim as first section → chapters as H2 → figures/tables inline with their section → references section → glossary (if source has one).

**Required frontmatter fields:** all defaults + `publisher`, `year`, `series` (optional), `page_count`, `executive_summary` (short, from first paragraphs of exec summary section).

**Success criteria:**
- Executive summary captured verbatim
- All chapters/sections accounted for
- Figure count in frontmatter matches figures in body
- Callout/box content preserved as blockquotes

**Default budget:** standard, escalates to deep if >200 pages

---

## book-longform

Monographs, edited volumes, policy books, long policy papers.

**Triggers:**
- File type: PDF or epub
- Size: >80 pages
- Structural signals: chapter headings, ISBN, table of contents, publisher metadata
- Content: narrative prose with sustained argument across chapters

**Engine preference:**
1. calibre (for epub)
2. Built-in `pdf` skill with per-chapter slicing
3. pymupdf with heading-based splitting
4. pdftotext + pandoc (last resort)

**Enrichment:** P3, P5, P6

**Output shape:**

**Always surface a split-confirmation to the user before executing** (cheap one-liner, not a full plan artifact):
> "This is a 240-page book — I'll split it into per-chapter files unless you'd rather have a single monolithic markdown. Say 'single-file' to override."

Default (per-chapter split):
```
<book-slug>/
  index.md                        # ToC, metadata, links to each chapter
  01-<chapter-slug>.md
  02-<chapter-slug>.md
  ...
  assets/                         # shared assets across chapters
    ...
```

Override (single-file): one `<book-slug>.md` with all chapters as H2s.

**Required frontmatter fields** (on index.md for split, or the single file): all defaults + `authors`, `publisher`, `year`, `isbn` (if available), `chapters` (count), `abstract` or `summary`.

**Success criteria:**
- Every chapter extracted
- Index is navigable with working relative links (for split)
- Chapter cross-references preserved
- Front matter (foreword, preface) included

**Default budget:** deep (always — books are worth planning)

---

## scanned-document

Historical reports, older publications, photocopied PDFs, anything without a reliable text layer.

**Triggers:**
- File type: PDF
- Text layer: missing, partial, or low-quality (garbled extraction)
- Visual signals: scan artifacts, skew, JPEG compression on text
- Page images dominate the file

**Engine preference:**
1. Built-in `pdf` skill OCR path (when available in the current host)
2. tesseract + pandoc (if available)
3. rapidocr (lightweight fallback)
4. **Loud failure** if no OCR available — do not silently produce garbage text

**Enrichment:** P3, P5 (minimal — focus on honest capture)

**Output shape:**
```
<doc-slug>.md
<doc-slug>-pages/                 # page images preserved for manual checking
  page-01.jpg
  ...
```

Body: page-by-page extracted text with `<!-- page N -->` markers. Low-confidence spans flagged inline with `<!-- low-confidence -->`.

**Required frontmatter fields:** all defaults + `ocr_confidence` (high | medium | low), `needs_review: true` (if confidence below high), `ocr_engine`.

**Success criteria:**
- Text extracted above confidence threshold, OR
- Honest failure with explicit next-steps note in the markdown body

**Default budget:** standard, escalates to deep if confidence is poor

**Hard rule:** never silently produce OCR garbage. If OCR fails or confidence is unacceptably low, the markdown body should say so explicitly, not bury it.

---

## simple-onepager

Factsheets, short briefs, one-page PDFs, simple Word documents, short notes.

**Triggers:**
- File type: PDF, docx, or html
- Size: ≤3 pages
- Layout: single column, mostly text
- Structure: minimal (maybe a heading and some paragraphs)

**Engine preference:**
1. Built-in `pdf` / `docx` skill
2. pandoc (for docx/html)
3. pymupdf (for PDF)
4. pdftotext (last resort)

**Enrichment:** P3 (if any images), P5

**Output shape:**
```
<doc-slug>.md                     # single file, frontmatter + body
```

**Required frontmatter fields:** all defaults only (no recipe-specific additions required).

**Success criteria:**
- No raw ligatures (fi, fl, ff) in output
- No page-break artifacts
- Frontmatter populated (even if some fields are `unknown`)
- Body is clean prose

**Default budget:** tight (this is the "just do it" lane)

---

## hybrid-novel

The catch-all for anything that doesn't cleanly match a recipe, or matches multiple weakly, or is a genuinely new source type.

**Triggers:**
- No recipe scored ≥5 in matching
- Document shows characteristics of two or more archetypes (e.g. a pitch deck PDF that's actually a hybrid report)
- Unfamiliar source type
- Agent judgment: "I don't know the right approach here"

**Engine preference:** decided in the plan

**Enrichment:** decided in the plan

**Output shape:** decided in the plan

**Required frontmatter fields:** all defaults + `recipe: hybrid-novel` + `approach_notes` (short description of what you did and why).

**Success criteria:** user approved the plan before execution; output matches the plan

**Default budget:** **deep — always writes a plan artifact and waits for review**

**Process:** write `<filename>.conversion-plan.md` covering:
1. What kind of source this is (your best characterisation)
2. Why it didn't match existing recipes
3. Which existing recipe comes closest and what you'd borrow from it
4. Proposed engine + enrichment + output shape
5. Success criteria you'll check against
6. Any open questions for the user

Then pause for review. Do not execute until the user approves or tweaks the plan.

If the same novel source type comes up twice, that's a signal to add a new recipe to the catalogue — flag it in the Verify report.
