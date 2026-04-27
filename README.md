# mdpowers

Markdown superpowers for knowledge gardens. A host-agnostic markdown-ingestion toolkit with canonical skills in `skills/`, Claude plugin packaging in `.claude-plugin/`, and Codex global-skill install support. Runs in Claude plugin hosts, Codex, Cursor, and other compatible agent environments.

## Skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `/convert` | "convert", "pdf to markdown", "docx to markdown", "pptx to markdown", "slide deck to markdown", upload a document | Adaptively converts any document (PDF, docx, pptx, epub, html, image) into structured, AI-readable markdown — with diagrams → mermaid, comparisons → tables, per-recipe enrichment, and graceful engine fallback |
| `/clip` | "clip this", "save this page", "defuddle", paste a URL | Fetches a web page via Defuddle, strips ads/nav/chrome, saves clean markdown with YAML frontmatter |
| `/transcribe` | "transcribe this", "transcribe video", "transcribe youtube", "transcribe audio", upload audio/video | Transcribes audio and video to structured, speaker-labelled markdown with adaptive vocabulary correction. Supports YouTube (native subs + Whisper API fallback), local files (WhisperX + pyannote diarization), and cloud API services (stub). |
| `/pdf-convert` | *(removed)* | **Removed in v0.4.** Use `/convert` instead. Knowledge bank and helper scripts migrated to `convert/references/`. |

## What makes `convert` different

`convert` isn't just another PDF-to-text extractor. It's an adaptive orchestrator that:

1. **Probes the source and environment** — file characteristics (type, layout, metadata), available tools (docling, marker, pymupdf, built-in Anthropic skills), and runtime constraints (RAM, disk)
2. **Matches the source to a recipe** — seven archetypes: slide deck, academic paper, institutional report, book, scanned doc, one-pager, hybrid-novel
3. **Picks the right engine** — prefers built-in Anthropic skills (`pdf`, `docx`, `pptx`, `xlsx`), falls back gracefully to docling, marker, pymupdf, or pandoc as the environment allows
4. **Enriches the output** — diagrams become mermaid, comparisons become tables, visuals get semantic descriptions, frontmatter gets populated per recipe, glossaries are built for documents with named concepts
5. **Verifies the result** — mechanical checks (asset refs resolve, frontmatter complete, no broken mermaid) plus recipe-specific success criteria
6. **Adapts the planning ceremony to the document** — tight budget for simple files (no ceremony), standard budget for most documents (inline narration), deep budget for novel or complex sources (plan artifact + user review before execution)

The core design principle is "guides not rails": recipes and playbooks are defaults, not mandates. Agents can deviate when they have specific reasons, and deviations are named in the narration so they're visible.

## Why markdown conversion helps agents

For many agent workflows, the real benefit of converting documents and pages into markdown or other clean structured text is not that markdown is magical. It is that clean text usually:

- removes irrelevant chrome and formatting noise
- preserves useful semantic structure like headings, lists, tables, and links
- makes chunking and retrieval easier
- gives agents source material they can quote, compare, and synthesize more reliably

In practice, this often reduces hallucination risk indirectly by improving grounding. The agent has cleaner evidence to work from, so search and synthesis tend to be better.

But there are real tradeoffs:

- conversion takes extra time up front
- interactive conversion and review can consume tokens
- OCR or extraction can introduce mistakes
- markdown can lose layout, positional, or visual detail that matters for forms, scans, dense tables, and highly designed PDFs

So the right claim is not "markdown always prevents hallucinations." The better claim is: clean markdown or structured text is often the best working format for retrieval, synthesis, and writing, while some source types still need layout-aware tools or the original document alongside the converted text.

See [`skills/convert/SKILL.md`](skills/convert/SKILL.md) for the full design, and [`DECISIONS.md`](DECISIONS.md) for the reasoning behind this architecture.

## Install

See [SETUP.md](SETUP.md) for full install instructions and compatibility matrix across Cowork, Claude Code, Codex, Cursor, Agent SDK, and direct API use.

## Dependencies

All dependencies use lazy installation — they're only probed when a skill is first invoked in a session, not at plugin startup. The `convert` skill probes what's available at runtime and falls back gracefully when a preferred tool is missing.

| Skill | Dependency | When needed | Install method |
|-------|-----------|-------------|----------------|
| `/convert` | Built-in `pdf`/`docx`/`pptx` skills | Always preferred when available | Native (no install) |
| `/convert` | pymupdf | Universal fallback for PDF | `pip install pymupdf --break-system-packages` |
| `/convert` | pandoc | docx, html, epub | `apt install pandoc` or `brew install pandoc` |
| `/convert` | docling (optional) | Hosts with ≥6GB RAM | `pip install docling --break-system-packages` |
| `/convert` | marker (optional) | Hosts with GPU or beefy CPU | `pip install marker-pdf --break-system-packages` |
| `/clip` | defuddle (npm) | Always | Auto-installed on first use at `$MDPOWERS_NODE_PREFIX` |

**Runtime requirements:** Python 3.10+ and Node 18+ on PATH, plus a writable home directory (or `MDPOWERS_NODE_PREFIX` set to a writable path). See [SETUP.md](SETUP.md) for the full contract.

## Project Structure

```
mdpowers-plugin/
├── README.md                       # this file — human-facing overview
├── AGENTS.md                       # canonical repo instructions
├── CLAUDE.md                       # Claude compatibility wrapper
├── SETUP.md                        # canonical install + compatibility reference (all hosts)
├── COMPATIBILITY.md                # stub redirecting to SETUP.md
├── DECISIONS.md                    # architectural decision log
├── ROADMAP.md                      # future directions
├── CHANGELOG.md                    # narrative change history
├── .gitignore
├── .claude-plugin/plugin.json      # plugin manifest
├── scripts/                        # host install/update helpers
└── skills/
    ├── convert/                    # adaptive document-to-markdown (v0.3)
    ├── clip/                       # web-page-to-markdown via Defuddle
    ├── transcribe/                 # audio/video to markdown + speaker labels + vocabulary
    └── (pdf-convert removed in v0.4; assets migrated to convert/references/)
```

## Design Principles

This plugin inherits the agentic-scaffold design principles. In brief:

1. **Guides not rails** — Recipes, playbooks, and phase instructions are defaults; agents can deviate with reason. Over-prescription is itself a failure mode.
2. **Progressive disclosure** — Root docs stay small; skill-specific detail lives in `skills/<name>/references/` and loads on demand.
3. **Dual-audience documentation** — README.md for humans, AGENTS.md for canonical agent instructions, CLAUDE.md as a thin compatibility wrapper.
4. **Adaptive over prescriptive** — Probe environment and source at runtime; don't assume fixed inputs or fixed tools.
5. **Graceful degradation** — Fall back silently when tools are missing; record quality downgrades in frontmatter. Never silently produce garbage.
6. **Decisions as first-class artifacts** — Significant choices get logged in DECISIONS.md before implementation.
7. **Source-grounded defaults** — Every convention traces to a documented source or a lesson from real usage.
8. **Host-agnostic by construction** — No hardcoded paths, no assumed tools, no branding to a specific host. Probe at runtime; degrade gracefully.

The full rationale for repo conventions is in [`AGENTS.md`](AGENTS.md).

## Roadmap

See [ROADMAP.md](ROADMAP.md) for planned work and future ideas. Highlights:

- Validating `convert` against real documents across all seven recipe archetypes
- `pdf-convert` removed in v0.4; knowledge bank migrated to `convert/references/`
- New playbooks for equation handling (P7), citation parsing (P8), figure-caption grounding (P9)
- New recipes for annual reports and legal contracts
- `process-inbox` and `research-clip` skills for tighter integration with knowledge garden workflows

## Contributing

Contributions welcome. Before making structural changes:

1. Read [AGENTS.md](AGENTS.md) for conventions and boundaries
2. Check [DECISIONS.md](DECISIONS.md) for prior architectural choices
3. Log new decisions before implementing them
4. Follow the skill-authoring conventions in AGENTS.md
5. Update CHANGELOG.md after significant work sessions
6. For portability or install-pathway changes, update [SETUP.md](SETUP.md) (the canonical reference; `COMPATIBILITY.md` is now a stub that redirects there)

## License

MIT

---

*This plugin uses the [agentic scaffold](https://github.com/montymerlin/agentic-scaffold) pattern for AI-assisted development.*
