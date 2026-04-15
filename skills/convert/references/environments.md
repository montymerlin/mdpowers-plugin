# Environment detection and engine routing

Probe detects the environment once per conversion. The results drive engine selection and degradation. This guide covers what to probe, how to interpret results, and the per-recipe engine preference lists with fallback rules.

For the supported-host matrix and the plugin's runtime contract (Python 3.10+, Node 18+, writable home), see the top-level `COMPATIBILITY.md`. This file is the agent-facing *how to probe*; COMPATIBILITY.md is the human-facing *what we support*.

## The environment profile

Probe produces a small profile with these fields:

```
environment: claude-code-macos | claude-code-linux | cowork-sandbox | cursor | desktop-app | ci-runner | unknown
ram_gb: <float>                    # soft probe, rounded
disk_free_gb: <float>              # in the working directory
network: full | limited | none     # can we pip install on demand?
tools:
  pymupdf: ✓ | ✗
  pandoc: ✓ | ✗
  docling: ✓ | ✗ (oom-risk if ram<6)
  marker: ✓ | ✗
  calibre: ✓ | ✗
  tesseract: ✓ | ✗
  rapidocr: ✓ | ✗
  pdftotext: ✓ | ✗
builtin_skills:
  pdf: ✓ | ✗
  docx: ✓ | ✗
  pptx: ✓ | ✗
  xlsx: ✓ | ✗
```

The `environment` field is a best-effort tag for narration and debugging — don't condition behaviour on it. Condition behaviour on `ram_gb`, `tools`, and `builtin_skills` instead. That way the plugin keeps working in hosts the tag doesn't recognise.

## How to detect each field

### Environment type
- Check `uname -a` for platform (Linux vs Darwin; Windows falls back to `unknown`)
- Check for Cowork session markers (path contains `/sessions/` + `.remote-plugins/` structure) → `cowork-sandbox`
- Check for Cursor MCP markers (env var `CURSOR_` prefix, or running under an MCP stdio transport) → `cursor`
- Check for CI markers (env vars `CI=true`, `GITHUB_ACTIONS`, `BUILDKITE`, etc.) → `ci-runner`
- Check for Claude Code (env var `CLAUDE_CODE_VERSION` or similar, if present) → `claude-code-macos` / `claude-code-linux`
- Fallback: `unknown` — this is fine; the concrete capability fields still drive decisions

### RAM
- Linux: `free -m` or read `/proc/meminfo` (MemTotal)
- macOS: `sysctl -n hw.memsize`
- Convert to GB, round to 1 decimal
- Soft probe — if it fails, assume 4GB (conservative default)

### Disk
- `df -h <working-dir>` → parse the Available column
- Convert to GB

### Network
- Attempt `pip install --dry-run <anything>` or a quick `curl -s --head https://pypi.org`
- If it times out or fails: `limited` or `none`
- In constrained sandboxes (Cowork, some CI runners), this is usually `limited` — some packages pre-installed, no fresh installs

### Tools
- `which <tool>` for each
- For Python tools: `python -c "import <tool>"` with `--break-system-packages` awareness
- Record the version if cheap to get (`<tool> --version` when it's fast)

**Special case — docling OOM risk:** even if docling is installed, flag it as unavailable if `ram_gb < 6`. Docling needs substantial memory and will be SIGKILL'd in tight environments. The Cowork sandbox with ~3.8GB RAM is the motivating case, but the rule applies to any host below the threshold (small CI runners, constrained containers, etc.). Record this as `docling: ✗ (oom-risk)` in the profile.

### Built-in skills
- Check whether the skill is listed in the active skills registry. Built-in skills from Anthropic (`pdf`, `docx`, `pptx`, `xlsx`) are typically available in Claude Code and the Claude desktop app (including Cowork mode), but **may not be available** in Cursor via MCP or in custom Agent SDK hosts. Always probe rather than assume.

## Engine preference lists

Each recipe declares an ordered preference list. Probe picks the highest-preference engine that's viable in the current environment.

### For PDF inputs

**Quality order (best → worst):**

1. **Built-in Anthropic `pdf` skill** — always first choice when available. Maintained by the people who trained the model. Handles layout, figures, tables, OCR, citations. Availability varies by host — probe first.
2. **marker** — heavy ML extractor; best quality for academic papers and complex layouts. Needs GPU or beefy CPU — typically only viable in unconstrained Claude Code environments.
3. **docling** — IBM's tool; good quality but memory-hungry. Requires RAM ≥6GB. OOMs reliably in low-RAM sandboxes (Cowork, small CI runners).
4. **pymupdf + post-processing** — universal fallback. Works in any environment with Python. Produces decent text extraction without layout analysis.
5. **pdftotext + pandoc** — last resort. Lowest quality but very fast and available almost everywhere.

### For docx inputs

1. **Built-in `docx` skill** — first choice
2. **pandoc** — reliable, widely available
3. **mammoth (Python lib)** — fallback for when pandoc is missing

### For pptx inputs

1. **Built-in `pptx` skill** — first choice
2. **python-pptx + pymupdf (for per-slide renders)** — fallback

### For epub inputs

1. **calibre (`ebook-convert`)** — gold standard
2. **pandoc** — fallback
3. **Built-in `pdf` skill** after converting epub→PDF — last resort

### For html inputs

Note: for URLs, use the `clip` skill instead. For local .html files:
1. **pandoc** — first choice
2. **defuddle** (if available) — fallback for messy HTML
3. **beautifulsoup + custom extraction** — last resort

### For images (single-page scans, screenshots)

1. **Built-in `pdf` skill** (wrap in a PDF first)
2. **tesseract** → markdown
3. **rapidocr** → markdown

## Graceful degradation rules

The degradation rule is simple: if the preferred engine fails or is unavailable, drop to the next one **without asking the user**. Only escalate if all viable engines have been tried and output still doesn't meet the recipe's success criteria.

**What counts as "engine failure":**
- Tool not installed or not on PATH
- Tool installed but crashes on this input (segfault, exception, OOM)
- Tool produces output but Verify phase rejects it (e.g. frontmatter can't be populated, asset references don't resolve, content is obviously garbled)

**How to degrade:**
1. Note the failure in your internal working state (don't show to user yet)
2. Move to the next engine in the preference list
3. If that engine succeeds, record `extracted_via: <engine>` AND `quality: degraded` in frontmatter (so downstream knows this could be re-converted later with a better engine)
4. Proceed normally with Enrich and Verify
5. In your final response, mention which engine ran and whether quality was degraded

**When to surface the degradation to the user:**
- Only if Verify ultimately rejects the output even after trying all engines
- Or if the degradation is severe enough to affect the recipe's success criteria (e.g. scanned doc with poor OCR, academic paper where 2-column bleed couldn't be fixed)

**What to never do:**
- Never silently produce garbage. If all engines fail, say so explicitly.
- Never skip Verify to "save time" on a degraded output.
- Never pretend the degraded engine's output is full quality — `quality: degraded` is a real field and matters for downstream re-conversion.

## Loud-failure cases

Two situations where Probe should stop and escalate immediately rather than degrade:

**1. OCR required but not viable.** Source is a scanned document (no text layer), no OCR engine is available in the environment. Stop. Tell the user:
- What the source is
- Why OCR is needed
- What engines would work (`pdf` skill, tesseract, rapidocr)
- Options: defer the conversion, run in a different environment, ask them to pre-OCR, or proceed with no-text output (not recommended)

**2. No viable engine at all.** Every engine in the preference list has failed or is missing. Don't produce output. Tell the user what was tried and what's missing.

These are the only two loud-failure cases. Everything else — suboptimal quality, missing enrichment because the engine doesn't support a feature, partial extraction — gets a `quality: degraded` flag and proceeds.

## Host routing check

Run this check at the end of Probe, **before** moving to Plan. It is a pre-flight check, not a failure — the goal is to route the user to a better environment when the job warrants it, not to block them.

### Detecting the host

```
Co-Work sandbox (constrained):
  - Working path contains /sessions/ AND .remote-plugins/ structure
  - OR env var CLAUDE_COWORK_SESSION is set
  - OR RAM < 5 GB (proxy for sandbox — constrained containers and Co-Work both hit this)

Claude Code (capable):
  - env var CLAUDE_CODE_VERSION is set
  - OR path does not contain /sessions/
  - When in doubt, probe RAM and tool availability — they tell you more than the label
```

### Classifying job complexity

**Simple job** (fine in any host):
- Single PDF with a text layer (pypdf extracts >500 chars/page on average)
- docx or pptx file ≤ 30 pages
- Single short HTML or web clip

**Complex job** (prefers Claude Code):
- PDF with no text layer (image-based / scanned) — requires OCR tool install
- PDF > 20 pages that needs layout analysis (docling/marker)
- Batch conversion (multiple files)
- Any job where the best engine requires `pip install` or `brew install`
- Any transcription (always complex — see transcribe skill)

### What to do

| Host | Job complexity | Action |
|---|---|---|
| Claude Code | Any | Proceed normally |
| Co-Work | Simple | Proceed normally |
| Co-Work | Complex | Surface routing recommendation (below), then ask whether to proceed anyway or switch |
| Unknown | Complex | Surface routing recommendation — user can decide |

**Routing recommendation message (use verbatim or adapt):**

```
⚠️  This is a complex conversion job that runs best in Claude Code.

Reason: [image-based PDF requiring OCR / large document needing docling / batch job]
Current environment: Co-Work sandbox — limited RAM, no brew/pip install, shorter timeouts.

To run this in Claude Code:
  1. Open a terminal
  2. cd to your project directory
  3. Run: claude
  4. Then ask: "Convert [filename] using mdpowers:convert"

Alternatively, I can attempt the conversion here with degraded quality. Proceed anyway? (y/n)
```

If the user says yes, proceed with `quality: degraded` in frontmatter and a note explaining the environment constraint. Never block silently — the user always has the final say.

## Probe output example

```
## Probe result

Source: Kwaxala Overview 2026.pdf
  - 25-page PDF, widescreen (1920×1080 aspect)
  - Low text density (~80 words/page average)
  - High image density (25 significant visuals)
  - No DOI, no ISBN, no academic metadata

Environment: cowork-sandbox (low-RAM)
  - RAM: 3.8 GB (tight — docling will OOM)
  - Disk: 9.6 GB free
  - Tools: pymupdf ✓, pandoc ✓, docling ✗ (oom-risk), marker ✗
  - Built-in skills: pdf ✓, docx ✓, pptx ✓

Recipe match: slide-deck-visual (score 9)
Engine selected: pymupdf (pdf skill not needed for slide renders; docling skipped due to OOM risk)
Quality expectation: full (pymupdf is the right tool for per-slide rendering anyway)
Budget: standard
```
