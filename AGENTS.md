# AGENTS.md — mdpowers

Canonical agent instructions for this repo. `CLAUDE.md` is a thin compatibility wrapper that points back here.

## What this repo is

`mdpowers` is a host-agnostic markdown-ingestion toolkit. It ships:

- canonical shared skills in `skills/`
- Claude plugin packaging in `.claude-plugin/`
- Codex global-install scripts in `scripts/`

The point is one source repo that can be consumed from multiple hosts without maintaining divergent copies.

## Canonical paths

- `AGENTS.md` is the canonical repo instruction file
- `CLAUDE.md` is a compatibility wrapper for Claude hosts
- `skills/` is the canonical skill payload directory
- `.claude-plugin/` is Claude-specific packaging metadata, not the source of truth for the skills themselves

## Working norms

- Read this file first on every session
- Treat `skills/` as the primary artifact; host-specific packaging should wrap it, not fork it
- Keep root-path handling host-agnostic. Prefer `MDPOWERS_ROOT`, then host-specific env vars, then documented defaults
- Log architectural choices in `DECISIONS.md` before or during implementation
- Update `CHANGELOG.md` after significant work sessions
- Keep `ROADMAP.md` aligned with actual host support and install/update workflow
- Never auto-commit; show the diff and wait for approval

## Compatibility rules

- No hardcoded session paths, home paths, or host-only assumptions
- Do not assume Claude plugin env vars exist when a skill can also run in Codex
- When a host-specific capability exists only in one runtime, name the limitation explicitly and degrade cleanly
- Docs should describe the canonical source repo first and host-specific install paths second

## Versioning

- `.claude-plugin/plugin.json` is the canonical release version for published plugin releases
- `CHANGELOG.md` headings that name a version must match `plugin.json`
- Patch releases are appropriate for documentation, compatibility, installer, and packaging improvements that do not change core skill behaviour

## Repo map

```text
mdpowers-plugin/
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── COMPATIBILITY.md
├── DECISIONS.md
├── ROADMAP.md
├── CHANGELOG.md
├── .claude-plugin/
├── scripts/
└── skills/
```

## Host model

- Claude plugin hosts consume `.claude-plugin/` + `skills/`
- Codex consumes installed skills from `~/.codex/skills/`
- The Codex install flow should point back to this repo checkout or to a vendor clone under `~/.codex/vendor_imports/repos/mdpowers-plugin`

## When editing skills

- Update current-facing references from `CLAUDE.md` to `AGENTS.md` where the guidance is repo-generic
- Keep historical changelog/decision references intact unless they are still presented as active guidance
- If a skill invokes bundled scripts, make the path resolution work in both plugin and Codex installs
