# CLAUDE.md — mdpowers

Markdown superpowers for knowledge gardens. A host-agnostic Claude Agent SDK plugin providing adaptive document-to-markdown conversion and web clipping, optimised for AI-readable output. Runs in Claude Code, Cursor, the Claude desktop app (Cowork mode), and any other Agent SDK host.

## Project Identity

- **Name:** mdpowers
- **Stack:** Claude Agent SDK plugin (skills + helper scripts in Python and JavaScript)
- **Purpose:** Turn documents (PDF, docx, pptx, epub, html, images) and web pages into clean, structured, AI-readable markdown
- **Repository:** https://github.com/montymerlin/mdpowers-plugin
- **Authored by:** Monty Merlin
- **Portability contract:** host-agnostic by construction. No hardcoded paths, no assumed tools, no host-specific branding. Everything is probed at runtime and degrades gracefully. See [COMPATIBILITY.md](COMPATIBILITY.md) for the supported-host matrix and runtime requirements.

## Directory Structure

```
mdpowers-plugin/
├── CLAUDE.md                       # this file — agent instruction set
├── README.md                       # human-facing overview
├── COMPATIBILITY.md                # host matrix + runtime contract
├── DECISIONS.md                    # architectural decision log
├── ROADMAP.md                      # future directions
├── CHANGELOG.md                    # narrative change history
├── .claude-plugin/
│   └── plugin.json                 # plugin manifest
└── skills/
    ├── convert/                    # v0.3 — adaptive document-to-markdown
    │   ├── SKILL.md
    │   └── references/
    │       ├── recipes.md
    │       ├── matching.md
    │       ├── environments.md
    │       ├── anti-patterns.md
    │       ├── roadmap.md
    │       └── enrichment/
    │           ├── P1-diagrams-to-structured.md
    │           ├── P2-comparisons-to-tables.md
    │           ├── P3-images-and-assets.md
    │           ├── P4-semantic-descriptions.md
    │           ├── P5-frontmatter-and-metadata.md
    │           └── P6-cross-references-and-glossary.md
    ├── clip/                       # web-page-to-markdown via Defuddle
    │   ├── SKILL.md
    │   └── scripts/md_defuddle.js
    └── pdf-convert/                # DEPRECATED in v0.3, removed in v0.4
        ├── SKILL.md                # deprecation notice + legacy docs
        ├── references/knowledge-bank.md
        └── scripts/
            ├── pdf_postprocess.py
            └── pdf_verify.py
```

## Key Conventions

### Skill authoring

- Each skill lives in `skills/<skill-name>/` with a `SKILL.md` at the root
- Long reference material (recipes, playbooks, catalogues) goes in `skills/<skill-name>/references/` and is loaded on demand
- Helper scripts (Python, JavaScript) go in `skills/<skill-name>/scripts/` and are invoked via `${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/scripts/...`
- Frontmatter descriptions must include the full trigger phrase vocabulary users are likely to say — ambiguity in triggering is the most common cause of skills not being invoked
- Every skill should articulate its own deviation guidance — "guides not rails" is the project-wide principle
- **Never hardcode host-specific paths** (session slugs, absolute home paths, Cowork mount points). Use `${CLAUDE_PLUGIN_ROOT}`, shell env vars, or probe at runtime. Portability is a first-class concern.

### Naming

- **Files:** kebab-case for markdown documents, snake_case for Python scripts, camelCase or kebab-case for JavaScript
- **Skills:** short, generic, memorable names (`convert`, not `adaptive-document-converter`). Skill namespace is `mdpowers:<skill>` (e.g., `mdpowers:clip`, `mdpowers:convert`).
- **Playbooks:** numbered `P1-*.md`, `P2-*.md`, etc. for easy cross-reference from recipes
- **Branches:** `feature/<short>`, `fix/<short>`, version branches like `v0.3-convert-skill`

### Versioning

- **Single source of truth:** `.claude-plugin/plugin.json` `version` field is the canonical version. Everything else references it.
- **Semver:** patch for skill tweaks and bug fixes, minor for new skills or significant feature additions, major for methodology overhauls or breaking changes.
- **Git tags on release:** Every version bump commit must be tagged (`git tag v0.4.2`). Tags are immutable anchors — commit messages mentioning versions without tags create the illusion of versioning without the mechanism.
- **Version-check before committing a bump:** Verify that `plugin.json` version, the latest CHANGELOG.md heading, and the commit message all agree. If they don't, fix them before committing. This is the most common source of version drift.
- **CHANGELOG headings name the version they describe** (e.g., `## 2026-04-15 — v0.4.2: ...`). The version in the heading must match what plugin.json says at that point in the commit history.

### Commits

- Concise message focusing on "why" not "what"
- Reference decisions by number when relevant (e.g., "per Decision 003")
- Never auto-commit — always show the diff first and wait for user approval

### Documentation

- **README.md** is the human-facing overview — what the plugin does, how to install, skill table
- **CLAUDE.md** (this file) is the agent instruction set — conventions, boundaries, directory map
- **COMPATIBILITY.md** is the portability contract — supported hosts, runtime requirements, per-host quirks
- **DECISIONS.md** logs architectural choices — add entries before implementing significant changes
- **ROADMAP.md** captures future directions — items flow to DECISIONS.md when evaluated
- **CHANGELOG.md** tracks evolution narratively — update after significant work sessions
- Skill-internal docs (like `convert/references/roadmap.md`) are scoped to that skill, not the whole plugin

## Agent Boundaries

### Do

- Read this file first on every session
- When adding new skills, follow the `convert` skill's structure (SKILL.md + references/ + scripts/)
- Prefer delegating to built-in Anthropic skills (`pdf`, `docx`, `pptx`, `xlsx`) before writing custom extractors
- Log decisions in DECISIONS.md before implementing structural changes
- Update CHANGELOG.md after significant work sessions
- Test new skills against real documents before shipping
- Bump the version in `.claude-plugin/plugin.json` for every release
- When adding a skill with a new dependency, update COMPATIBILITY.md

### Don't

- Auto-commit changes — always show the diff first
- Hardcode paths (session slugs, absolute home paths, Cowork mount points) — use `${CLAUDE_PLUGIN_ROOT}`, env vars, or runtime probes
- Hardcode assumptions about environment (RAM, installed tools, host type) — probe at runtime
- Write helper scripts when an existing library or built-in skill would work
- Reference the removed `pdf-convert` skill — it was removed in v0.4, assets migrated to `convert/references/`
- Duplicate content between files — reference instead
- Bundle heavy dependencies at install time — use lazy loading on first skill invocation
- Brand the plugin to a single host ("Cowork plugin", "Claude Code plugin") — it's host-agnostic

## Design Principles

1. **Guides not rails** — Recipes, playbooks, and phase instructions are defaults, not mandates. Agents can deviate when they have specific reasons; deviations must be named for transparency. Over-prescription is itself a failure mode.

2. **Progressive disclosure** — Root files stay small (README, CLAUDE.md). Skill-specific details live in `skills/<name>/references/` and are only loaded when that skill is invoked. This follows Anthropic's Agent Skills three-level model (metadata → instructions → nested files).

3. **Dual-audience documentation** — README.md serves humans, CLAUDE.md serves agents. Don't collapse one into the other. Skill SKILL.md files are agent-facing; their references are agent-facing too. There's no human-facing skill documentation — that's what the README is for.

4. **Adaptive over prescriptive** — Skills should probe the environment and match source archetypes to recipes at runtime, not assume a fixed input format or a fixed execution environment. The `convert` skill is the canonical example.

5. **Graceful degradation** — When a preferred tool isn't available, fall back silently and record the quality downgrade in frontmatter. Never silently produce garbage; loudly flag failures that matter.

6. **Decisions as first-class artifacts** — Significant structural choices get logged in DECISIONS.md before implementation. This creates a searchable trail that survives memory loss.

7. **Source-grounded defaults** — Every convention should trace to a documented source or a specific lesson learned from real usage. No convention exists "because it seemed right."

8. **Host-agnostic by construction** — No hardcoded paths, no assumed tools, no branding to a specific host. The plugin works wherever the Agent SDK loads plugins. When in doubt, probe; when probing fails, degrade.

## Key Skills Overview

### convert (primary skill, v0.3)

Adaptive document-to-markdown orchestrator. Five phases: Probe → Plan → Execute → Enrich → Verify. Seven-recipe catalogue. Six enrichment playbooks. Handles PDF, docx, pptx, epub, html, image. Replaces `pdf-convert`.

Entry point: `skills/convert/SKILL.md`.

### clip (v0.2+)

Web-page-to-markdown via Defuddle. Strips ads/nav/chrome, saves clean markdown with YAML frontmatter. In v0.3.1 the install bootstrap was made host-agnostic (previously had session-slug paths hardcoded).

Entry point: `skills/clip/SKILL.md`.

### pdf-convert (REMOVED in v0.4)

Docling-first PDF converter. Deprecated in v0.3, removed in v0.4. Knowledge bank and helper scripts (`pdf_postprocess.py`, `pdf_verify.py`) migrated to `skills/convert/references/`. Use `convert` for all document-to-markdown work.

## References

- [README.md](README.md) — human-facing overview and install guide
- [COMPATIBILITY.md](COMPATIBILITY.md) — supported hosts, runtime contract, per-host quirks
- [DECISIONS.md](DECISIONS.md) — architectural decision log
- [ROADMAP.md](ROADMAP.md) — future directions and inspiration
- [CHANGELOG.md](CHANGELOG.md) — narrative change history

<!-- Scaffold sources: Anthropic CLAUDE.md conventions, HumanLayer CLAUDE.md best practices, Anthropic Agent Skills architecture, agentic-scaffold-plugin v0.1.0 -->
