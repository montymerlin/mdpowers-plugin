# Roadmap — future evolution of the convert skill

Future work is documented here so the trajectory is visible without bloating v1. **Don't build ahead** — items below only move into the skill proper when real usage reveals a concrete need.

## v0.2 (current)

This release. Single `convert` skill with:
- Five-phase workflow (Probe → Plan → Execute → Enrich → Verify)
- Three-tier planning budget (tight / standard / deep)
- Seven-recipe catalogue
- Six enrichment playbooks (P1–P6)
- Runtime environment detection with graceful degradation
- "Guides not rails" design principle
- Deprecates `pdf-convert` (kept on disk for backward compatibility)

## v0.3 — enrichment depth

Triggered when: real usage shows gaps in enrichment coverage for specific document types.

Likely additions:

- **Equation handling playbook (P7)** — preserve LaTeX / MathML from academic sources. Matters for Frontiers, PNAS, and other math-heavy venues.
- **Citation parsing playbook (P8)** — extract CSL-JSON from references sections so citations become queryable. Useful for the academic-paper and book-longform recipes.
- **Figure-caption grounding (P9)** — link each figure to the paragraph(s) that reference it, via anchor links. Makes the output navigable like the source.
- **Annual report recipe** — distinct from institutional-report. Triggers on corporate annual reports with financial sections, governance disclosures, and forward-looking statements.
- **Legal contract recipe** — triggers on contract-like PDFs (numbered clauses, signature blocks, defined terms sections). Specialised enrichment: defined-term extraction, clause numbering preservation, change-tracking if present.

## v0.4 — multi-skill decomposition (conditional)

Triggered **only** if the monolithic `convert` skill starts feeling cramped or users need to invoke phases independently.

Potential split (from the Approach C alternative considered during design):

- `convert-plan` — Probe + Plan only. Outputs a plan artifact, no execution.
- `convert-execute` — takes a plan, runs Execute + Enrich.
- `convert-verify` — takes a converted file, runs Verify independently.

This split only happens if there's a real demand pattern like "just give me the plan, I'll execute it myself" or "re-verify this file I already converted last month." Otherwise the phases stay internal to `convert` and don't need to be separate skills.

## v1.0 — QMD integration + feedback loops

Triggered when: the commons reaches a scale where per-conversion learning becomes worth building infrastructure for.

Potential additions:

- **Automatic QMD indexing** — converted files get registered with QMD immediately, so they become searchable without manual steps.
- **Feedback store** — a lightweight log of pitfalls encountered in past conversions (e.g. "docling OOM'd in a low-RAM sandbox on this file size", "marker produced 2-column bleed on this journal") that the next Probe reads to avoid repeating mistakes.
- **Self-updating recipe catalogue** — when deviations from recipes are logged consistently, the catalogue updates to reflect the learned patterns.
- **Cross-document reconciliation** — detect when two converted docs cite the same source and auto-link them.

v1.0 is aspirational. It represents where the skill *could* go, not a commitment.

## Always-stretch (may never happen)

Ideas that are neat but not clearly worth the complexity:

- **Web-page-to-markdown unification with `clip`** — merge `convert` and `clip` into a single entry point that dispatches by input type. Cleaner UX but loses the clear separation between URL-based and file-based sources.
- **Batch inbox processing** — a `convert --batch <folder>` mode that processes every document in a folder and produces a unified index. Some users want this; most sessions are per-document.
- **Cross-document diff** — "how did this policy doc change from v1 to v2" as a first-class operation. Niche but valuable when it matters.
- **Multilingual support** — the current skill assumes English-ish output. Full multilingual handling (language detection, per-language enrichment rules, translation options) is a significant undertaking.

## Explicitly out of scope (intentional)

These are design choices, not missing features:

- **Prose quality editing** — `convert` is a mechanical correctness tool. Prose quality review is handled by the Superpowers `two-stage-review` skill separately (if installed).
- **Content generation** — `convert` doesn't write new content. It only transforms existing content.
- **Format conversion to non-markdown targets** — `convert` is specifically document-to-markdown. If you need markdown-to-docx or markdown-to-pdf, use the built-in `docx`/`pdf` skills directly.
- **Real-time OCR of live camera input** — `convert` operates on files, not streams.

## How to propose additions

If usage reveals a gap, the update path is:

1. Document the gap in `docs/known-issues.md` (new file to be created if not present) with: what source type hit the gap, what went wrong, what would have worked
2. When 2+ instances of the same gap accumulate, write a new recipe or playbook draft
3. Test the draft on the accumulated examples
4. Add to the skill proper if it works

Avoid pre-emptively building for hypothetical cases. The design principle is: let usage drive the catalogue, don't let the catalogue drive the design.
