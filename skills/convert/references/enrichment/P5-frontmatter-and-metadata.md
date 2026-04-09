# P5 — Frontmatter and metadata

The YAML frontmatter contract. Every converted document gets a frontmatter block. This playbook defines the required and recipe-specific fields, how to extract them, and how to handle missing values.

## Why frontmatter matters

Frontmatter is how converted documents become searchable, navigable, and programmatically processable. Other agents and tools — QMD indexes, the research commons INDEX.md generator, Notion sync, static site generators — all read frontmatter to understand what a file is. A file without frontmatter is invisible to tooling; a file with wrong or missing frontmatter is actively misleading.

Frontmatter is also the primary signal for downstream re-conversion: the `quality: degraded` field and the `extracted_via` field tell future agents which files are candidates for re-processing when better engines become available.

## The required contract (all recipes)

Every conversion, regardless of recipe, produces frontmatter with these fields. They are non-negotiable — if you can't populate a field truthfully, use `unknown` rather than leaving it blank.

```yaml
---
title: <string>
source_file: <relative path from working dir to original>
source_type: pdf | docx | pptx | epub | html | image | other
recipe: <recipe slug used, e.g. slide-deck-visual>
extracted_via: <engine + version, e.g. "pymupdf 1.23.6">
converted_on: <YYYY-MM-DD>
quality: full | degraded
---
```

**Field guide:**

- **`title`** — Extract from the document's actual title, not the filename. Look in: document metadata (docx core properties, PDF info dict), first H1, cover page text, slide 1 title. If multiple candidates, prefer the most complete. If truly unknown, use a clean version of the filename as fallback: `Kwaxala Overview 2026` not `kwaxala-overview-2026.pdf`.

- **`source_file`** — Relative path from the output file's directory to the source. Not absolute. Example: `kwaxala/Kwaxala Overview 2026.pdf`.

- **`source_type`** — The file extension, lowercased and dot-stripped. `pdf`, `docx`, `pptx`, `epub`, `html`, `image`, or `other`.

- **`recipe`** — The slug of the recipe used (from `references/recipes.md`). If you deviated from the recipe's defaults significantly, still record the recipe here and explain in `approach_notes` (see hybrid-novel).

- **`extracted_via`** — Which engine actually ran. Format: `<tool> <version>` when version is easy to get, otherwise just `<tool>`. Examples: `pymupdf 1.23.6`, `pandoc 3.1.9`, `docling 2.69.1`, `anthropic-pdf-skill`, `pymupdf+pandoc` (for pipelines). This field matters for debugging and for re-conversion decisions.

- **`converted_on`** — ISO date of the conversion. Use the actual current date, not "today" or relative terms.

- **`quality`** — Either `full` (primary engine succeeded, all enrichment applied) or `degraded` (fell back from preferred engine, or enrichment was partial). If degraded, add a `quality_notes` field explaining why.

## Recipe-specific fields

Each recipe layers additional required fields on top of the contract. These are enforced by Verify.

### slide-deck-visual additions

```yaml
slides: <integer count>
deck_type: pitch | lecture | report | other
summary: <1-2 sentence summary of what the deck is about>
tags: <list of relevant topic tags>
```

### academic-paper additions

```yaml
authors: <list of strings, "First Last" format>
doi: <string or "none">
journal: <string or "preprint" or "unknown">
year: <integer>
abstract: <string — the paper's abstract verbatim>
```

### institutional-report additions

```yaml
publisher: <string — e.g. "IPBES", "FAO", "WRI">
year: <integer>
series: <string or null>          # e.g. "IPBES Assessment Series"
page_count: <integer>
executive_summary: <string — first 2-3 paragraphs of the exec summary section>
authors: <list — editors, contributors, or lead authors if available>
```

### book-longform additions

```yaml
authors: <list>
publisher: <string>
year: <integer>
isbn: <string or "none">
chapters: <integer count>
summary: <1-2 paragraph summary>
```

### scanned-document additions

```yaml
ocr_confidence: high | medium | low
ocr_engine: <string>
needs_review: true | false        # true if confidence below high
```

### simple-onepager additions

No required additions beyond the default contract. Keeps it minimal.

### hybrid-novel additions

```yaml
approach_notes: <string — explains what you did and why>
closest_recipe: <slug of the recipe you borrowed from most>
```

## How to extract each field

### Title extraction
1. **docx/pptx:** read core properties (`cp:title` or `dc:title` in the metadata)
2. **PDF:** read `/Title` from the info dict (pymupdf: `doc.metadata["title"]`)
3. **Fallback:** largest/first H1 in the body
4. **Fallback:** cover page / slide 1 text (usually the biggest text on the page)
5. **Last resort:** cleaned filename

### Authors
1. **docx/pptx:** core properties `dc:creator`
2. **PDF:** info dict `/Author`
3. **Academic papers:** first-page author block (usually after title, before abstract)
4. **Books:** title page, usually the line below the title
5. **Institutional reports:** often in acknowledgments, credits page, or front matter

If multiple separators are present ("Smith, J., Doe, J., & Lee, K."), normalise to `["Smith, J.", "Doe, J.", "Lee, K."]`.

### DOI
1. Search first 2 pages for `doi:` or `https://doi.org/` patterns
2. Regex: `10\.\d{4,9}/[-._;()/:A-Z0-9]+` (case insensitive)
3. If multiple DOIs found (article + references), take the one closest to the top
4. If none found: `"none"` (explicit, not null)

### Abstract
1. Find the "Abstract" heading (case insensitive, various formats: "Abstract", "ABSTRACT", "Summary")
2. Extract text until next heading or section break
3. Trim whitespace, preserve paragraphs within as a single string with `\n\n` separators
4. If missing: use the first substantive paragraph after the title/authors as a fallback, and note this in `quality_notes`

### Publisher
1. PDF metadata `/Producer` is sometimes it, often not (usually the PDF creation tool)
2. Cover page / title page — look for organisation names, logos (the logo itself might tell you, but you'd need to read it)
3. Footer text on content pages ("© 2024 IPBES", "United Nations Environment Programme")
4. Document title sometimes includes the publisher ("An FAO Report on...")

### Year
1. PDF metadata `/CreationDate`
2. Cover page date
3. Copyright line
4. Reference list style (ISO dates visible in citations can suggest publication era)

### Summary / executive_summary
Write your own summary if the document doesn't provide one. Keep it under 3 sentences for `summary`. For `executive_summary` on institutional reports, capture the first 2-3 paragraphs of the source's own executive summary verbatim.

### Tags
This is the most subjective field. Aim for 3-8 tags that would help someone searching the knowledge base find this document. Use lowercase, kebab-case for multi-word tags. Prefer existing tag vocabulary over inventing new ones (check the working directory for other files' tags and reuse where applicable).

For Bridging Worlds specifically, common tags include: `refi`, `nature-finance`, `bioregional`, `indigenous-stewardship`, `carbon-markets`, `localism`, `commons`, `tokenisation`, `web3`, `cosmos-sdk`, `land-trusts`.

## Handling missing values

Three strategies in order of preference:

1. **Extract from context** — if the source doesn't explicitly state the field but it can be inferred from context (e.g. publisher from a cover logo described in surrounding text), do that and note the inference in `quality_notes`.

2. **Explicit unknown** — if the field truly can't be determined, write `unknown` as the value. Never leave a required field blank or `null` (except where the schema explicitly allows null, like `series`).

3. **Flag for review** — if a required field is unknown AND the document is important enough to warrant human follow-up, add `needs_review: true` to the frontmatter.

## Anti-patterns

- **Inventing fields not in the recipe's spec.** Don't add `author_email` or `version` or `pagination` unless the recipe defines them.
- **Using relative dates.** `converted_on: today` is wrong. `converted_on: 2026-04-09` is right.
- **Leaving required fields blank.** `title:` with nothing after is a Verify failure.
- **Making up values to pass Verify.** If you don't know the DOI, don't invent one. `"none"` is the correct answer.
- **Ignoring the `quality` field.** Every conversion ends with either `full` or `degraded`. Never omit it.

## Example — a clean academic-paper frontmatter

```yaml
---
title: "The ecological footprint of carbon offset markets: a critique"
source_file: papers/ecological-footprint-offsets.pdf
source_type: pdf
recipe: academic-paper
extracted_via: anthropic-pdf-skill
converted_on: 2026-04-09
quality: full
authors:
  - "Smith, Jane A."
  - "Doe, John B."
  - "Lee, Kyung"
doi: "10.1038/s41559-024-02345-6"
journal: "Nature Ecology & Evolution"
year: 2024
abstract: |
  Carbon offset markets have grown rapidly over the past decade, but the
  ecological integrity of the credits traded on these markets remains
  contested. In this paper we review evidence from 127 peer-reviewed
  studies examining the additionality, permanence, and leakage of
  forest-based offset projects...
tags:
  - carbon-markets
  - forest-offsets
  - additionality
  - nature-finance
  - critique
---
```

## Example — a degraded conversion frontmatter

```yaml
---
title: "Kwaxala Overview 2026"
source_file: kwaxala/Kwaxala Overview 2026.pdf
source_type: pdf
recipe: slide-deck-visual
extracted_via: pymupdf 1.23.6
converted_on: 2026-04-09
quality: degraded
quality_notes: "docling unavailable in this environment (low-RAM sandbox, OOM risk); pymupdf fallback used. Slide renders are good but some in-slide text extraction may be missing."
slides: 25
deck_type: pitch
summary: "A 25-slide overview of the Kwaxala initiative — a regenerative forest finance stack combining Tenured Forest Land, Living Forest Standard, Catalytic Commitment Facility, and Living Forest Fund."
tags:
  - bioregional
  - forest-finance
  - indigenous-stewardship
  - living-forest-standard
  - refi
---
```

The `quality: degraded` + `quality_notes` is the key signal here. Future agents running in Claude Code can grep for `quality: degraded` and re-convert with docling/marker to improve the output.
