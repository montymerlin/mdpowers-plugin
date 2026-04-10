# Compatibility

`mdpowers` is a Claude Agent SDK plugin. It follows the standard plugin contract (`.claude-plugin/plugin.json` + `skills/<name>/SKILL.md`) and runs in any host that supports Agent SDK plugins. The plugin makes no assumption about which host is loading it — all environment-specific details are probed at runtime.

## Supported hosts

| Host | Status | Install | Notes |
|------|--------|---------|-------|
| **Claude Code** | Supported | `claude plugins install github.com/montymerlin/mdpowers-plugin` or clone and symlink into `~/.claude/plugins/` | Primary development environment. Built-in `pdf`/`docx`/`pptx`/`xlsx` skills available for delegation. |
| **Claude desktop app (Cowork mode)** | Supported | Drop the plugin directory into your Cowork plugins folder | Tight-RAM sandbox — `docling` is skipped and `pymupdf` is used instead. Graceful degradation handles this automatically. |
| **Cursor (via MCP)** | Supported | Add as an MCP server in Cursor settings | Skills appear as tool calls. Built-in Anthropic skills are not available here — `convert` falls back to `pymupdf`/`pandoc`. |
| **Claude Agent SDK (custom host)** | Supported | Follow the Agent SDK plugin loading docs | Works anywhere the SDK runs, provided Python and Node are on PATH. |
| **Anthropic API (direct tool use)** | Partial | No plugin loader; copy skill instructions into a system prompt and implement tool bindings yourself | Skills are markdown + scripts, so the content is portable, but you'll need to wire up the tool invocations by hand. |

## Runtime contract

The plugin assumes:

- **Python 3.10+** on PATH (for `convert`'s Python fallbacks: `pymupdf`, `pandoc`, optional `docling`, optional `marker`)
- **Node 18+** on PATH (for `clip`'s Defuddle wrapper)
- **Writable home directory** or `MDPOWERS_NODE_PREFIX` set to a writable path (for lazy `defuddle` install)
- **Working directory access** via `${CLAUDE_PLUGIN_ROOT}` (standard in Agent SDK)

Everything else is detected at runtime. The plugin never assumes a specific path layout, a specific RAM ceiling, or which tools are pre-installed. See `skills/convert/references/environments.md` for the full detection procedure.

## Transcribe skill pathways

The `/transcribe` skill supports three pathways with different host/tool requirements:

| Pathway | Availability | Host support | Best use |
|---------|--------------|--------------|----------|
| **P1 — YouTube fast** | All hosts + network | Claude Code, Cursor, Cowork, CI | Extracting native YouTube captions + Whisper API fallback. Fastest, no local tools needed. |
| **P2 — WhisperX local** | Hosts with ≥6GB RAM + GPU/CPU | Claude Code (macOS/Linux), Cursor, custom hosts | High-quality local transcription with speaker diarization. Requires WhisperX + pyannote pre-installed. |
| **P3 — Cloud API (stub)** | Hosts with network + API credentials | All hosts | Placeholder for custom SaaS transcription services. Implementation left to users per provider. |

Transcribe probes available tools at runtime and selects the best pathway automatically (P1 → P2 → P3). Users can override with explicit reasoning. Vocabulary cascade uses `$XDG_CONFIG_HOME/mdpowers/transcribe/` for user-extensible term lists.

## Environment detection

When `convert` and `transcribe` run their Probe phases, they produce a profile with these fields:

```
environment: claude-code-macos | claude-code-linux | cowork-sandbox | cursor | desktop-app | ci-runner | unknown
ram_gb: <float>
disk_free_gb: <float>
network: full | limited | none
tools: { pymupdf, pandoc, docling, marker, calibre, tesseract, rapidocr, pdftotext, whisperx, pyannote }
builtin_skills: { pdf, docx, pptx, xlsx }
transcribe_pathways: { p1_available, p2_available, p3_available }
```

Detection is "soft" — if probing a field fails, it uses a conservative default rather than blocking execution. RAM defaults to 4GB if unprobable; tools default to ✗ if `which` fails; transcribe pathways default to P1 (always available if network exists) with P2/P3 marked ✗ if dependencies are missing.

## Known environment quirks

**Low-RAM sandboxes (Cowork, small CI runners) — `docling` OOMs and `transcribe` P2 unavailable.** Docling and WhisperX each need ~6GB to run safely. Below that, they get SIGKILL'd. The convert skill probes RAM and flags `docling: ✗ (oom-risk)` when `ram_gb < 6`; transcribe probes and marks `p2_available: ✗ (oom-risk)`, falling back to P1 (YouTube) or P3 (if configured). This is recorded as `quality: degraded` in the output frontmatter so the file can be re-processed later in a beefier environment.

**Cursor and pure-MCP hosts — no built-in Anthropic skills.** The `convert` skill prefers delegating to built-in `pdf`/`docx`/`pptx`/`xlsx` skills when they're present. In hosts where those aren't available, it falls through to the next engine in the preference list. No configuration needed. Transcribe works normally (all three pathways available if tools are installed).

**Sandboxes without network — no lazy installs and no P1 transcribe.** `clip` lazy-installs `defuddle` on first use; `transcribe` P1 requires network for YouTube/Whisper API. If the environment has no network access, both fail and the skills report the install/network error. Pre-install `defuddle` at `$MDPOWERS_NODE_PREFIX` or pre-download WhisperX models to `$XDG_CACHE_HOME/mdpowers/` to work around this.

**Read-only home directory.** If `$HOME` isn't writable, set `MDPOWERS_NODE_PREFIX` (for clip) and `XDG_CONFIG_HOME`/`XDG_CACHE_HOME` (for transcribe) to writable paths. This is rare — most Agent SDK hosts provide a writable home.

## What the plugin does NOT assume

- A specific directory structure in the working workspace (no hardcoded `research/`, `projects/`, etc. — the clip skill checks for a workspace `CLAUDE.md` or `README.md` to derive conventions if present)
- A specific session-slug path prefix (`/sessions/...`, `/home/user/...`, etc. — everything uses `${CLAUDE_PLUGIN_ROOT}` or shell env vars)
- The presence of any specific tool — everything is probed
- A particular operating system — the env probe handles macOS, Linux, and should degrade cleanly on Windows (untested — report issues)
- A minimum RAM — the probe records what's available and recipes degrade accordingly

## Testing portability

To verify the plugin works in a new host:

1. **Load the plugin** following that host's install instructions
2. **Invoke `/convert` on a small PDF** and check the Probe output — environment should be detected, tools should be enumerated, a recipe should match
3. **Check the output frontmatter** — `extracted_via` should name a real engine, `quality` should be `full` or `degraded` (not missing)
4. **Invoke `/clip` on a test URL** and verify Defuddle installs and runs without manual path intervention

If any of these fail, check `skills/convert/references/environments.md` for the probe logic and `skills/clip/SKILL.md` for the install bootstrap. Portability regressions should be logged in `DECISIONS.md`.

## Reporting portability issues

If the plugin fails on a new host, open an issue at [github.com/montymerlin/mdpowers-plugin](https://github.com/montymerlin/mdpowers-plugin) with:

- Host name and version (e.g., "Claude Code 1.2.3", "Cursor 0.38", "Cowork desktop 2026-04-09")
- Output of the Probe phase if `convert` got that far
- Which engine was selected and how it failed
- Relevant env vars (`CLAUDE_PLUGIN_ROOT`, `MDPOWERS_NODE_PREFIX`, `PATH`)
