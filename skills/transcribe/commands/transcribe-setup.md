---
name: transcribe setup
description: Initialize vocabulary files, check dependencies, and configure the transcribe skill for your environment.
---

# /transcribe setup

Run this once per machine to configure the transcribe skill. Idempotent — running it again updates existing config rather than overwriting.

## What it does

1. Detects your OS and XDG data paths
2. Creates or updates your global master vocabulary file
3. Optionally creates a project-local vocabulary overlay scoped to your current repo
4. Captures your host path (Cowork sandbox mode only)
5. Updates `.gitignore` to exclude cache files
6. Checks environment variables (`OPENAI_API_KEY`, `HF_TOKEN`)
7. Probes installed dependencies and offers to install missing ones
8. Pre-fetches WhisperX models if Path 2 deps are installed

## Implementation

- **Local mode** (Claude Code, Cursor): runs `scripts/setup_wizard.py` interactively
- **Sandbox mode** (Cowork): the skill drives the same steps via chat UI, following `references/setup-sandbox.md`

## When to run

- First time using the transcribe skill
- After moving to a new machine
- After cloning a project that uses vocabulary overlays
- When you want to add Path 2 dependencies to an existing setup
