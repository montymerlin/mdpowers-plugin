# CLAUDE.md — Compatibility Wrapper

Before doing anything else in this repo, Read `AGENTS.md` in full. It is the canonical instruction set for this repo; this file is a thin Claude compatibility wrapper and assumes you have read `AGENTS.md` first.

In Claude Code (CLI), an `@AGENTS.md` directive will expand recursively. In Cowork (desktop), that expansion is not reliable, so the explicit imperative above is required — do not skip it.

## Claude-specific Notes

- `.claude-plugin/` is the packaging contract for Claude plugin hosts.
- `.claude/settings.local.json` is local Claude configuration, not canonical repo state.
- When the repo mentions `plugin.json` as the release-version source of truth, that refers to `.claude-plugin/plugin.json`.
