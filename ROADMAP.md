# Roadmap — mdpowers

Where this plugin could go. Items here are aspirations, not commitments — a place to capture ideas, inspiration, and future directions without the pressure of a deadline.

When an item is evaluated and chosen (or declined), the outcome moves to the Decided section below with a pointer to the relevant entry in [DECISIONS.md](DECISIONS.md).

**Statuses:** `active` (in progress) · `idea` (worth evaluating) · `parked` (inspiration, no timeline) · `decided` (evaluated — see DECISIONS.md)

---

## Near-term

Items likely to be addressed in the next development cycle.

- **Validate `convert` against real documents** — Run the new skill on 3-5 documents of different archetypes (Kwaxala-style deck, Frontiers paper, IPBES report, one-page brief, scanned doc) and tune recipes based on what works and what breaks. Log observations to a new `docs/known-issues.md`. `status: active`

- **P4 Podcast RSS runner** (`transcribe` skill) — The P4 pathway spec is now documented in `references/pathways/P4-podcast-rss.md`. The pathway is currently executed manually (Podcast Index API via WebFetch, curl download, delegate to P2). Next step: a `scripts/podcast_rss.py` runner that automates the discover → check-transcript → download → delegate flow. Needs Podcast Index API key wired into env, Buzzsprout signed-CDN pattern codified, and `podcast:transcript` tag parser. `status: idea`

- **P3 API service implementation** (`transcribe` skill) — Implement the cloud transcription service API stub (currently placeholder). Establish the contract for per-provider authentication (API keys), test with ≥1 real SaaS provider (e.g., AssemblyAI, Rev), update anti-patterns and output format docs. `status: idea`

- **Batch playlist handling** (`transcribe` skill) — Support P1 (YouTube) bulk transcription with a playlist URL, emit a unified index markdown with per-video chapters and timestamps. Low-hanging fruit for power users who want to transcribe workshop series, courses, or multi-part talks in one go. `status: idea`

- **Vocabulary auto-promotion** (`transcribe` skill) — Implement the frequency-based cascade logic that promotes custom vocabulary items to standard when they appear consistently across multiple transcriptions. Currently the infrastructure is in place (custom/standard split), the promotion logic is a stub. `status: idea`

- **Cross-skill convert↔transcribe handoff** — When a user provides a video file that's encoded as MP4/WebM with audio, detect this and suggest transcribing the audio track instead of trying to convert the whole file. Conversely, when transcribing a presentation video, suggest converting the visible deck (if available separately) to structured slides. This is a "would you like to..." suggestion, not automatic. `status: idea`

- **~~Remove `pdf-convert` in v0.4~~** — Done. Removed in v0.4. Knowledge bank and helper scripts migrated to `skills/convert/references/`. `status: done`

- **Tag and publish v0.4.2 to GitHub** — Tag the current state (`git tag v0.4.2`) and push. This is the first properly tagged release — previous versions were tracked in CHANGELOG and commit messages but never anchored with git tags. `status: idea`

- **Portability test matrix** — Verify the plugin loads and runs in at least three hosts (Claude Code, Cursor via MCP, Cowork desktop app). Document any per-host quirks in COMPATIBILITY.md. Adds a "Tested on:" badge line to the README. `status: idea`

## Future explorations

Ideas worth evaluating when the time is right. No commitment, but worth thinking about.

- **Source resolution cascade skill** — Formalise the OA API cascade (Unpaywall → Semantic Scholar → EuropePMC → CrossRef → Wayback → WebFetch) as a dedicated resolution step or sub-skill that `clip` can invoke whenever a URL is academic or DOI-bearing. Goal: make the plugin "resilient by default" against paywalls and bot-blocks, not just in the failure-handling docs but as executable first-class logic. Would need a DOI detection heuristic and per-host API rate-limit management. **Consumer coordination:** research-workflow skills (e.g. a `sources-commons`-style commons orchestrator) can invoke this cascade as a capture primitive rather than reimplementing it. The cascade lives here; consumers call it. `status: idea`

- **Abstract-level capture as first-class output tier** — Currently `capture_failed: true` is binary: either full text or nothing. A middle tier — abstract + metadata, clearly flagged — would be more useful for academic sources. Semantic Scholar returns abstracts even for closed-access papers; CrossRef returns bibliographic metadata for almost everything. A `capture_tier: abstract` field in frontmatter (alongside `capture_failed: false`) would let downstream work distinguish "full text captured", "abstract only", and "stub/failed". `status: idea`

- **Sci-Hub integration (legal-context only)** — Sci-Hub maintains a community mirror of academic papers that are otherwise paywalled. In contexts where Sci-Hub access is legally authorised (e.g. researchers in jurisdictions that permit it, or when working with papers already in personal possession under first-sale doctrine), adding a Sci-Hub lookup step to the OA cascade would significantly increase the hit rate for academic paper capture. Implementation would require: explicit user opt-in (never default), jurisdiction awareness or user acknowledgement, and a clear note in frontmatter that the source was retrieved via Sci-Hub. The legal status of Sci-Hub access varies by jurisdiction — this feature must be documented as requiring user understanding of their local copyright law. `status: parked`

- **Image downloading for `clip`** — The `clip` skill currently captures the OG `image:` URL in frontmatter but doesn't download images locally. A future iteration could download referenced images to a sibling `{name}-assets/` folder (consistent with the `-assets/` convention already established in `convert`'s P3 playbook) and update inline references to relative paths. Key design constraint: **preserve the original remote URL alongside the local copy** — either in frontmatter or as a `<!-- source: URL -->` comment next to each image reference — so the clip remains attributable to its source. Research (April 2026) found the `-assets/` naming aligns with MarkDownload and Docusaurus; `assets/` (centralised) and `_artifacts/` (Docling/Pandoc-style) are alternatives worth considering for consistency. `status: idea`

- **Equation handling playbook (P7)** — Preserve LaTeX / MathML from academic sources. Matters for Frontiers, PNAS, and other math-heavy venues. Would extend the `academic-paper` recipe. `status: idea`

- **Citation parsing playbook (P8)** — Extract CSL-JSON from references sections so citations become queryable. Useful for the `academic-paper` and `book-longform` recipes and for cross-document reconciliation. `status: idea`

- **Figure-caption grounding (P9)** — Link each figure to the paragraphs that reference it, via anchor links. Makes the output navigable like the source. `status: idea`

- **`annual-report` recipe** — Distinct from `institutional-report`. Triggers on corporate annual reports with financial sections, governance disclosures, and forward-looking statements. Specialised enrichment: financial table extraction, MD&A section handling, risk factors parsing. `status: idea`

- **`legal-contract` recipe** — Triggers on contract-like PDFs (numbered clauses, signature blocks, defined terms sections). Specialised enrichment: defined-term extraction, clause numbering preservation, change-tracking if present. `status: idea`

- **Multi-skill decomposition** — Split `convert` into `convert-plan` / `convert-execute` / `convert-verify` if real usage shows the phases need independent invocation (e.g. "just give me the plan, I'll execute it myself"). This is Approach C from the original design brainstorm — deferred in v0.3 in favour of a monolithic skill with internal phases. `status: idea`

- **`process-inbox` skill** — Triage and route items from a configurable inbox directory into the appropriate knowledge destination. Reads frontmatter and content to suggest the right target (readings, research, wisdom, etc.), applies missing metadata, moves the file, and optionally triggers QMD indexing. This is the "second half" of the clipping workflow — currently done manually. **Consumer coordination:** mdpowers `clip`/`convert`/`transcribe` can write to a user-specified inbox directory; downstream workflow skills (e.g. a research-commons orchestrator) pick items up from there and route them into project structure. The inbox path is a consumer concern, not an mdpowers concern — this skill just needs to respect whatever `output_dir` or `inbox_dir` the caller specifies. `status: idea`

- **`research-clip` skill** — Research-aware variant of `clip`. When working within a specific research domain, clips a URL into a caller-specified references directory, creates or updates a research log entry noting what was clipped and why. Combines clip + file + log in one action. **Scope question:** partially superseded when a caller has a full research-commons workflow that already orchestrates clip + index-update + session-log. `research-clip` may still have a role for ad-hoc clipping into research directories that aren't backed by a full commons. Revisit scope once the `clip` primitive has been used by a second independent commons-style workflow. `status: idea`

## Parking lot

Inspiration, references, repos, articles, and possibilities. Things seen or thought of that might be relevant someday. No commitment, no timeline — just a place so good ideas don't get lost.

- **QMD integration** — Bundle a QMD MCP server connection in the plugin's `.mcp.json` so clipped/converted content can be immediately indexed and searchable without a separate `qmd update && qmd embed` step. Open question: in hosts where QMD is already configured at the workspace or user level, bundling it here would duplicate the server definition. Worth exploring whether the plugin can reference an existing parent-scope MCP config or whether it needs its own. `status: parked`

- **Feedback store for conversion pitfalls** — A lightweight log of pitfalls encountered in past conversions (e.g. "docling OOM'd on this file size in a low-RAM sandbox", "marker produced 2-column bleed on this journal") that the next Probe reads to avoid repeating mistakes. Would require a persistent store outside the plugin itself. `status: parked`

- **Self-updating recipe catalogue** — When deviations from recipes are logged consistently, the catalogue updates to reflect learned patterns. Needs the feedback store above. `status: parked`

- **Cross-document reconciliation** — Detect when two converted docs cite the same source and auto-link them. Would need citation parsing (P8) to land first. `status: parked`

- **Web-page-to-markdown unification with `clip`** — Merge `convert` and `clip` into a single entry point that dispatches by input type. Cleaner UX but loses the clear separation between URL-based and file-based sources. `status: parked`

- **Batch inbox processing** — `convert --batch <folder>` mode that processes every document in a folder and produces a unified index. Some users want this; most sessions are per-document. `status: parked`

- **Cross-document diff** — "How did this policy doc change from v1 to v2" as a first-class operation. Niche but valuable when it matters. `status: parked`

- **Multilingual support** — The current skill assumes English-ish output. Full multilingual handling (language detection, per-language enrichment rules, translation options) is a significant undertaking. `status: parked`

- **Marker integration** — Marker is another ML-based PDF extractor with strong academic paper handling. Currently listed as a preference in the `academic-paper` recipe but not tested end-to-end. `status: parked`

## Decided

Items that have been evaluated. The reasoning lives in [DECISIONS.md](DECISIONS.md) — this section just tracks the outcome.

- **Adopt agentic scaffold** — → Decision 001. `status: decided`
- **Replace pdf-convert with adaptive convert skill** — → Decision 002. `status: decided`
- **"Guides not rails" as project-wide principle** — → Decision 003. `status: decided`
- **Prefer built-in Anthropic skills as first-choice engines** — → Decision 004. `status: decided`
- **Rename to `mdpowers` and decouple from Cowork branding** — → Decision 005. `status: decided`
- **Version reconciliation and versioning convention** — → Decision 010. `status: decided`

<!-- Scaffold sources: GitHub roadmap patterns, Mozilla Science roadmapping guide, agile parking lot conventions, YAGNI principle, agentic-scaffold-plugin v0.1.0 -->
