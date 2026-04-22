# CLAUDE.md — Compatibility Wrapper

Canonical repo instructions live in [AGENTS.md](AGENTS.md). Read that first and treat it as the source of truth.

This file exists only as a Claude-host compatibility layer.

## Claude-specific Notes

- `.claude-plugin/` is the packaging contract for Claude plugin hosts.
- `.claude/settings.local.json` is local Claude configuration, not canonical repo state.
- When the repo mentions `plugin.json` as the release-version source of truth, that refers to `.claude-plugin/plugin.json`.
