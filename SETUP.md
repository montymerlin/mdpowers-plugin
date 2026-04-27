# Setup Guide

Adaptive document-to-markdown conversion (PDF, docx, pptx, epub, html, image), web clipping, and transcription with graceful fallbacks across constrained hosts.

---

## Quick Install (for AI agents)

If you're an AI agent installing this plugin, **detect the host first**, then pick the matching path. Only ask the user the questions explicitly listed below.

```
1. Detect host:
   ├── Cowork (Claude Desktop, sandboxed)
   │     → Path A: Cowork upload (no questions needed)
   │     → Note: low-RAM sandbox; docling auto-skipped, pymupdf used. No user choice needed.
   │
   ├── Claude Code CLI (terminal, has `claude` command)
   │     → Path B: claude plugins install
   │     → ASK USER: "Install globally (every project) or locally (this project)?"
   │       • global → `claude plugins install github.com/montymerlin/mdpowers-plugin`
   │       • local  → symlink `ln -s <path> ./.claude/plugins/mdpowers`
   │
   ├── Codex (terminal, has `codex` command or $CODEX_HOME set)
   │     → Path C: bash scripts/install_codex_skills.sh --from-github
   │     → ASK USER (only if non-default): "Update from GitHub or use current checkout?"
   │       Default to --from-github unless the user is actively editing the repo.
   │
   ├── Cursor (has Cursor MCP config)
   │     → Path D: Add MCP server entry to .cursor/mcp.json
   │
   └── Unknown / custom Agent SDK host
         → Path E: Standard plugin loader; verify Python 3.10+ and Node 18+ on PATH first.
```

**Host detection signals:**
- `$CLAUDE_COWORK == "1"` or `mount | grep virtiofs` matches → Cowork
- `command -v claude` succeeds and not Cowork → Claude Code CLI
- `command -v codex` succeeds or `$CODEX_HOME` is set → Codex
- `~/.cursor/` exists → Cursor
- Otherwise → ask the user which environment they're in.

**Required dependencies (verify before install regardless of host):**
- Python 3.10+ on PATH (for `convert` engines)
- Node 18+ on PATH (for `clip`'s Defuddle wrapper)
- Writable home directory or `$MDPOWERS_NODE_PREFIX` set

If those aren't satisfied, surface the problem to the user before continuing the install.

---

## Compatibility Matrix

| Host | Status | Install | Notes |
|------|--------|---------|-------|
| **Cowork** | Supported | Upload `ops/plugins/_dist/mdpowers-0.4.3.plugin` | Tight-RAM sandbox — `docling` skipped, `pymupdf` used instead. Graceful degradation automatic. |
| **Claude Code CLI** | Supported | `claude plugins install github.com/montymerlin/mdpowers-plugin` | Primary development environment. Built-in `pdf`/`docx`/`pptx`/`xlsx` skills available for delegation. |
| **Codex** | Supported (skills-only) | `bash scripts/install_codex_skills.sh --from-github` | Global skills install; points back to vendor clone. No `.claude-plugin/`. |
| **Cursor (via MCP)** | Supported | Add as MCP server in Cursor settings | Skills appear as tool calls. No built-in Anthropic skills — `convert` falls back to `pymupdf`/`pandoc`. |
| **Claude Agent SDK** | Supported | Plugin loader docs + Python 3.10+, Node 18+ on PATH | Works anywhere SDK runs. Environment probed at runtime. |
| **Anthropic API (direct)** | Partial | Manual tool wiring from SKILL.md | Skills are portable; bind tool invocations by hand. |

## Install Steps

### Cowork

You need a `.plugin` zip to upload. Get one of these three ways:

**Option 1 — pre-built release (preferred when available):**
Download `mdpowers-<version>.plugin` from the GitHub Releases page of `montymerlin/mdpowers-plugin`.

**Option 2 — built locally from this repo:**

```bash
git clone https://github.com/montymerlin/mdpowers-plugin.git
cd mdpowers-plugin
zip -r /tmp/mdpowers-0.4.3.plugin . \
  -x "*.DS_Store" "*/__pycache__/*" "*.pyc" ".git/*" "node_modules/*" "*.log" "_dist/*"
```

The output `/tmp/mdpowers-0.4.3.plugin` is your upload artifact.

**Option 3 — built by the workspace `cowork-plugin-packager` skill** (montymerlinHQ collaborators only):
The packaged file lives at `ops/plugins/_dist/mdpowers-0.4.3.plugin` after running the skill.

Then upload:

1. Open Claude Desktop → **Cowork** → **Plugins**.
2. Click **+ Add plugin** → **Upload a file** → select `.plugin`.
3. Skills appear under `/`: `/convert`, `/clip`, `/transcribe`.

**Pre-upload verification (recommended):**

```bash
# Confirm the manifest is at the zip root
unzip -l /tmp/mdpowers-0.4.3.plugin | head -20

# Confirm size is under 50 MB (this plugin packages to ~221 KB)
du -h /tmp/mdpowers-0.4.3.plugin
```

**Known quirks:**
- Some Claude Desktop builds reject `.plugin` extension at upload dialog. Workaround: rename to `.zip` (contents identical). See [anthropics/claude-code#28337](https://github.com/anthropics/claude-code/issues/28337) and [#40414](https://github.com/anthropics/claude-code/issues/40414).
- Cowork is a low-RAM sandbox — `docling` is auto-skipped (would OOM), `pymupdf` used instead. No user action required; output frontmatter records `quality: degraded` so files can be re-processed in beefier environments.

### Claude Code CLI

Two install scopes — **ask the user which one fits**:

- **Global** (every project on this machine): `claude plugins install github.com/montymerlin/mdpowers-plugin`
- **Local** (this project only, lives in `./.claude/plugins/`): symlink the cloned repo

**Global install:**

```bash
claude plugins install github.com/montymerlin/mdpowers-plugin
```

**Local install** (project-scoped):

```bash
git clone https://github.com/montymerlin/mdpowers-plugin.git ~/src/mdpowers-plugin
mkdir -p ./.claude/plugins
ln -s ~/src/mdpowers-plugin ./.claude/plugins/mdpowers
```

Skills load automatically in `/` menu once installed. `convert` will preferentially delegate to Claude Code's built-in `pdf`/`docx`/`pptx`/`xlsx` skills when available.

### Codex (Global Skills)

From any checkout of the mdpowers repo:

```bash
bash scripts/install_codex_skills.sh --from-github
```

This installs three global skills (`mdpowers-clip`, `mdpowers-convert`, `mdpowers-transcribe`) that point to:

```
~/.codex/vendor_imports/repos/mdpowers-plugin
```

Update later:

```bash
bash ~/.codex/vendor_imports/repos/mdpowers-plugin/scripts/update_codex_skills.sh
```

To point at your current working checkout:

```bash
export MDPOWERS_ROOT="$(pwd)"
bash scripts/install_codex_skills.sh --force
```

### Cursor (MCP)

Add to `.cursor/mcp.json` or `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "mdpowers": {
      "command": "npx",
      "args": ["-y", "mdpowers-mcp"]
    }
  }
}
```

Restart Cursor. Skills appear as tool calls.

## Runtime Contract

The plugin requires:

- **Python 3.10+** on PATH (for `convert` fallbacks: `pymupdf`, `pandoc`, optional `docling`, optional `marker`)
- **Node 18+** on PATH (for `clip`'s Defuddle wrapper)
- **Writable home directory** or `MDPOWERS_NODE_PREFIX` set to writable path (lazy `defuddle` install)
- **Repo root locator** via `MDPOWERS_ROOT`, `${CLAUDE_PLUGIN_ROOT}`, or default Codex vendor path: `${CODEX_HOME:-$HOME/.codex}/vendor_imports/repos/mdpowers-plugin`

Everything else is probed at runtime. No hardcoded paths, no assumed tools, no minimum RAM. See `skills/convert/references/environments.md` for full detection.

## Transcribe Skill Pathways

| Pathway | When available | Best for |
|---------|-----------------|----------|
| **P1 — YouTube fast** | All hosts + network | Extracting native YouTube captions + Whisper API fallback. Fastest. |
| **P2 — WhisperX local** | Hosts with ≥6GB RAM + GPU/CPU | High-quality local transcription with speaker diarization. |
| **P3 — Cloud API (stub)** | Hosts with network + API credentials | Custom SaaS transcription services (user-implemented). |

Skill probes at runtime and selects best pathway automatically (P1 → P2 → P3). Override with explicit reasoning.

## Environment Detection Profile

When `convert` and `transcribe` run their Probe phases:

```
environment: claude-code-macos | claude-code-linux | cowork-sandbox | cursor | desktop-app | ci-runner | unknown
ram_gb: <float>
disk_free_gb: <float>
network: full | limited | none
tools: { pymupdf, pandoc, docling, marker, calibre, tesseract, rapidocr, pdftotext, whisperx, pyannote }
builtin_skills: { pdf, docx, pptx, xlsx }
transcribe_pathways: { p1_available, p2_available, p3_available }
```

Detection is soft — missing fields default to conservative values. RAM defaults to 4GB if unprobable. Tools default to ✗ if `which` fails.

## Known Quirks

**Low-RAM sandboxes (Cowork, small CI runners) — `docling` OOMs and `transcribe` P2 unavailable**

Docling and WhisperX each need ~6GB. Below that, they get SIGKILL'd. The `convert` skill probes RAM and flags `docling: ✗ (oom-risk)` when `ram_gb < 6`. Transcribe marks `p2_available: ✗ (oom-risk)`, falling back to P1 (YouTube) or P3 (if configured). Output frontmatter records `quality: degraded` so files can be re-processed later in beefier environments.

**Cursor, Codex, pure-MCP hosts — no built-in Anthropic skills**

`convert` prefers delegating to built-in `pdf`/`docx`/`pptx`/`xlsx` skills when present. When unavailable, falls through gracefully. No configuration needed.

**Sandboxes without network — no lazy installs and no P1 transcribe**

`clip` lazy-installs `defuddle` on first use; `transcribe` P1 requires network. If environment has no network, both fail and report the error. Pre-install `defuddle` at `$MDPOWERS_NODE_PREFIX` or pre-download WhisperX models to `$XDG_CACHE_HOME/mdpowers/` to work around.

**Read-only home directory**

If `$HOME` isn't writable, set `MDPOWERS_NODE_PREFIX` (for clip) and `XDG_CONFIG_HOME`/`XDG_CACHE_HOME` (for transcribe) to writable paths.

**.plugin vs .zip extension issue**

Tracked in [anthropics/claude-code#28337](https://github.com/anthropics/claude-code/issues/28337) and [#40414](https://github.com/anthropics/claude-code/issues/40414). Some Cowork builds reject `.plugin` at upload dialog. Rename to `.zip` (contents identical) as workaround.

**Plugin size limit**

50 MB (Cowork sandbox). mdpowers is 221 KB — no issue.

## Testing Portability

To verify the plugin works in a new host:

1. Load the plugin following that host's install instructions.
2. Invoke `/convert` on a small PDF and check Probe output — environment should be detected, tools enumerated, recipe matched.
3. Check output frontmatter — `extracted_via` should name a real engine; `quality` should be `full` or `degraded` (not missing).
4. Invoke `/clip` on a test URL and verify Defuddle installs and runs without manual path intervention.

If any fail, check `skills/convert/references/environments.md` for probe logic and `skills/clip/SKILL.md` for install bootstrap. Log regressions in `DECISIONS.md`.

## Reporting Issues

Open an issue at [github.com/montymerlin/mdpowers-plugin](https://github.com/montymerlin/mdpowers-plugin) with:

- Host name and version (e.g., "Claude Code 1.2.3", "Cowork 2026-04-09")
- Probe phase output if `convert` reached it
- Which engine was selected and how it failed
- Relevant env vars: `MDPOWERS_ROOT`, `CLAUDE_PLUGIN_ROOT`, `MDPOWERS_NODE_PREFIX`, `PATH`
