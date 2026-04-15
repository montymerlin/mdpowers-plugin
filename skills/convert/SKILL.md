---
name: convert
description: Adaptively convert documents (PDF, Word, PowerPoint, and more) into clean, AI-readable markdown. Use when the user asks to "convert" a document, "turn this into markdown", "extract text from", "process this file", "pdf to markdown", "docx to markdown", "pptx to markdown", "slide deck to markdown", or provides a document they want as markdown. This skill replaces the older pdf-convert skill and handles any document-to-markdown conversion adaptively — it picks the right engine for the environment, matches the source to the closest archetype in its recipe catalogue, applies appropriate enrichment (diagrams → mermaid, comparisons → tables, visuals → semantic descriptions), and verifies the output against recipe-specific success criteria.
---

# convert

> **Guides not rails.** Everything below is a default, not a mandate. Recipes, playbooks, and phase instructions exist so you don't have to re-derive good choices every time — not to override your judgment when you can see something the catalogue can't. If a document would be better served by a different approach, take that approach, name what you did differently, and proceed. The worst failure mode isn't "deviated from the playbook" — it's "followed the playbook blindly and produced something worse than judgment would have." Hard rails are listed in `references/anti-patterns.md`. Everything else is soft.

## What this skill does

Converts any document (PDF, docx, pptx, epub, html, image) into markdown optimised for agentic processing. The output isn't just extracted text — it's a structured, enriched, verified representation that other agents and humans can navigate, search, and reason over.

## When to use

- User asks to convert any document to markdown
- User uploads a PDF, Word, or PowerPoint file and wants its content as markdown
- User wants a document added to a research commons or knowledge base
- User references the current `pdf-convert` skill (which this skill replaces)

## The five phases

Every conversion moves through five phases. The phases are conceptual — they are not procedural bureaucracy. In tight budget mode (simple documents) they collapse into a single sentence of narration. In deep budget mode (novel or complex documents) each phase may get its own pass with user review.

1. **Probe** — classify the source file and detect the environment
2. **Plan** — pick a recipe, decide the planning budget, proceed silently or surface a plan
3. **Execute** — run the chosen engine to extract text and assets
4. **Enrich** — apply recipe-specific enrichment (diagrams, tables, descriptions, frontmatter, glossary)
5. **Verify** — run mechanical checks and recipe success criteria, produce a short report

## Planning budget — the adaptive core

Not every document needs the same treatment. Probe drives the budget choice:

**Tight budget** — for simple, well-understood sources:
- One-page PDFs, simple docx, short articles, factsheets
- Auto-pick recipe, execute, minimal enrich, verify
- No plan artifact, no questions, no ceremony
- Budget overhead: two sentences in your response explaining what you did

**Standard budget** — the default for most documents:
- Academic papers, institutional reports, standard slide decks, normal-length docx
- Pick recipe and state the choice inline ("treating this as an academic paper; will extract figures and build cross-ref glossary")
- No separate plan file — the plan is transparent narration in your response
- Budget overhead: short paragraph of what you're doing and why

**Deep budget** — reserved for novel, complex, or hybrid sources:
- Books (>80 pages), hybrid documents that don't cleanly match a recipe, scanned docs with poor OCR, anything where the right approach isn't obvious
- Draft a plan file next to the output (`<filename>.conversion-plan.md`)
- Pause for user review before executing
- Budget overhead: several minutes and user involvement — but only when warranted

**How to choose budget:**
- Start by assuming tight
- Escalate to standard if the document has structure worth preserving (figures, tables, chapters, multi-section layout)
- Escalate to deep if: (a) no recipe scores ≥5 in matching, (b) the document is >200 pages, (c) it's a book, (d) it's a hybrid of multiple archetypes, (e) OCR quality is degraded, or (f) you genuinely don't know the right approach

Escalation is cheap. Under-planning is expensive. When in doubt, escalate one level.

## Phase 1 — Probe

Probe runs two parallel detections:

**(a) Source characteristics.** Read `references/environments.md` for the full probe guide. Short version: run a single pymupdf pass (or equivalent for non-PDF formats) to extract file type, size, page count, column layout, aspect ratio, text-to-image ratio, metadata (DOI, ISBN, authors, abstract), and structural signals (heading depth, section count, ToC presence).

**(b) Environment capabilities.** Detect what tools are actually available: RAM, disk, installed tools (docling, marker, pandoc, pymupdf, calibre, tesseract, rapidocr), installed Python packages, network access, and which built-in Anthropic skills can be delegated to (`pdf`, `docx`, `pptx`, `xlsx`).

**(c) Host routing check.** After detecting the environment, classify the job as simple or complex and check whether the current host can handle it well. See the full routing logic in `references/environments.md` under "Host routing check". If the job is complex and the host is Co-Work or constrained, surface a routing recommendation to the user before proceeding to Plan.

Output: a short profile you carry into Plan. Example:
```
Source: 25-page PDF, widescreen, image-heavy, 0.3 text-image ratio — likely slide deck
Environment: low-RAM sandbox (3.8GB), pymupdf ✓, docling ✗ (OOM risk), built-in pptx ✓
```

## Phase 2 — Plan

Score the source against the recipe catalogue in `references/recipes.md` using the rubric in `references/matching.md`. Highest-scoring recipe wins if it scores ≥5; otherwise fall through to `hybrid-novel` and escalate to deep budget.

Pick an engine from the recipe's ordered preference list, filtered to what the environment supports. **Always prefer built-in Anthropic skills** (`pdf`, `docx`, `pptx`, `xlsx`) when they cover the need — they are maintained by the people who trained you.

Decide budget (tight/standard/deep) using the rules above. Then:
- **Tight:** proceed to Execute silently, with one sentence of narration
- **Standard:** state the recipe and engine choice inline, then proceed to Execute
- **Deep:** write a `<filename>.conversion-plan.md` covering recipe, engine, enrichment steps, output shape, and success criteria — then pause for user review

## Phase 3 — Execute

Run the chosen engine. Extract text and assets according to the recipe's output shape specification. If the primary engine fails (tool missing, OOM, crash), silently degrade to the next engine in the preference list. Only escalate to the user if all viable engines have failed.

Record which engine actually ran — this becomes the `extracted_via` field in frontmatter. If you fell back from a higher-quality engine, record `quality: degraded` in frontmatter so downstream work knows this file could benefit from re-conversion later.

## Phase 4 — Enrich

Apply the enrichment playbooks the recipe references. Each playbook lives in `references/enrichment/` as its own file. Recipes list playbook IDs (P1–P6) in their Enrichment field.

The core playbooks:
- **P1** — `diagrams-to-structured.md` — turn flowcharts, process diagrams, and layered stacks into image + prose description + mermaid (or structured fallback)
- **P2** — `comparisons-to-tables.md` — detect before/after, this/that, extractive/regenerative framings and extract to markdown tables
- **P3** — `images-and-assets.md` — standard treatment for images, photos, figures (format, resolution, folder conventions, alt text)
- **P4** — `semantic-descriptions.md` — how to write the prose description that accompanies visuals (the AI-readability bridge)
- **P5** — `frontmatter-and-metadata.md` — the YAML frontmatter contract, required and recipe-specific fields
- **P6** — `cross-references-and-glossary.md` — build a short glossary at the bottom of documents that introduce named concepts, acronyms, or initiatives

Enrichment is where most of the AI-readability value gets added. Treat it seriously. If a recipe's enrichment list seems wrong for this specific document (e.g. a book that has no diagrams), adapt — skip playbooks that don't apply, borrow playbooks from other recipes that do.

## Phase 5 — Verify

Mechanical correctness checks — fast, specific, actionable. Five checks:

1. **Frontmatter completeness** — every required field for the chosen recipe is present and non-empty (required fields listed in P5)
2. **Asset reference integrity** — every image and link reference in the markdown resolves to an actual file on disk
3. **Structural sanity** — valid markdown, no orphan YAML, no unclosed code blocks, no broken mermaid syntax
4. **Recipe success criteria** — the outcome checks declared by the recipe (e.g. "every slide has image + description", "abstract in frontmatter", "ToC section present")
5. **Size and content sanity** — output isn't suspiciously tiny, isn't truncated mid-sentence, doesn't contain obvious OCR garbage (ligature artifacts, glyph IDs)

Produce a short Verify report at the end of your response: what passed, what degraded, what (if anything) needs follow-up. When a check fails, be specific and actionable: not "verification failed" but "frontmatter missing `doi` field (recipe: academic-paper). Attempted extraction from first page found no DOI match — source may not have one. Suggest: set `doi: none` manually or confirm this isn't actually a preprint."

Verify is a mechanical correctness checker, not a prose quality editor. For prose quality review, invoke the `two-stage-review` skill separately.

## Commons-awareness

If you detect a `CLAUDE.md` in the working tree, read it and honour any conventions it declares. Specifically watch for:
- Filename conventions (kebab-case slugs, special cases)
- Directory conventions (where converted files belong, asset subfolder patterns)
- Index regeneration hooks (e.g. `python .scripts/generate_index.py`)
- Commit policy (whether to auto-commit or show diff first)

Commons-awareness is a soft detection — when it fires, **name what's being applied** at the start of your response so the user can see it ("Detected Bridging Worlds CLAUDE.md — using kebab-case slugs, placing output in research/, will remind you to regenerate INDEX.md after").

## References

- `references/recipes.md` — the seven-recipe catalogue (archetypes + their specifications)
- `references/matching.md` — recipe scoring rubric used by Probe
- `references/environments.md` — environment detection guide + per-recipe engine preference lists
- `references/enrichment/P1-diagrams-to-structured.md` — diagram handling
- `references/enrichment/P2-comparisons-to-tables.md` — comparison extraction
- `references/enrichment/P3-images-and-assets.md` — image and asset handling
- `references/enrichment/P4-semantic-descriptions.md` — prose descriptions for visuals
- `references/enrichment/P5-frontmatter-and-metadata.md` — YAML frontmatter contract
- `references/enrichment/P6-cross-references-and-glossary.md` — glossary construction
- `references/anti-patterns.md` — hard rails (the few things that are non-negotiable)
- `references/roadmap.md` — future evolution (v0.3, v0.4, v1.0 trajectory)

## Relationship to other skills

`convert` leans on other skills rather than reimplementing them:

- **Built-in Anthropic skills** — `pdf`, `docx`, `pptx`, `xlsx`. Always preferred as engines when they cover the need. `convert` is the orchestrator; these are the workers. Availability varies by host — see `references/environments.md` and the top-level `COMPATIBILITY.md` for the full matrix.
- **`mdpowers:clip`** — for web-page-to-markdown. `convert` and `clip` are siblings; if the source is a URL, use `clip`; if it's a file, use `convert`.
- **Removed:** `mdpowers:pdf-convert` — the old docling-first PDF converter, removed in v0.4. Its knowledge bank and helper scripts now live in `references/knowledge-bank.md`, `references/pdf_postprocess.py`, and `references/pdf_verify.py`.
- **Superpowers skills** (if installed) — `two-stage-review` for prose quality review after conversion, `brainstorming` for genuinely novel sources where Probe can't match any recipe. Namespace varies by how the user installs the Superpowers plugin (`superpowers:...` or `superpowers-cowork:...`). These are optional siblings, not hard dependencies.
