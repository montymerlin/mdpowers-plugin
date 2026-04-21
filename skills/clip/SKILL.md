---
name: mdpowers:clip
description: >
  Clip web pages to clean markdown using Defuddle. Use when the user asks to
  "clip this", "save this page", "defuddle", "web clip", "save this url",
  "clip to markdown", "save as markdown", "grab this article", "clip article",
  "save this link", "convert page to markdown", or provides a URL they want
  saved as markdown. Also trigger when the user pastes a URL and asks to
  "read", "save", or "capture" it.
---

# Clip — Web Page to Markdown

Clip any web page to a clean markdown file using Defuddle. Strips navigation, ads, and chrome — keeps the article content with structured YAML frontmatter.

## Setup

Defuddle must be available before the first clip in a session. The install location is resolved at runtime so this works across Claude Code, Cursor, the desktop app, and Cowork without hardcoded session paths. Run this silently before the first clip — don't ask the user, just do it:

```bash
# Resolve a writable, portable install prefix (works on any host)
MDP_NODE_PREFIX="${MDPOWERS_NODE_PREFIX:-${XDG_DATA_HOME:-$HOME/.local/share}/mdpowers/node}"
mkdir -p "$MDP_NODE_PREFIX"
export PATH="$MDP_NODE_PREFIX/bin:$PATH"

# Install only if missing — cheap no-op on subsequent runs
command -v defuddle >/dev/null 2>&1 || npm install -g defuddle --prefix "$MDP_NODE_PREFIX" 2>/dev/null
```

Verify with `defuddle --version` (expect 0.15.0+). If it fails, re-run the install without `2>/dev/null` to see errors.

**Override:** set `MDPOWERS_NODE_PREFIX` in the environment before invoking the skill if the default location isn't writable (rare — some sandboxes may need this).

## How to Clip

The plugin bundles a Node.js script at `${CLAUDE_PLUGIN_ROOT}/skills/clip/scripts/md_defuddle.js`.

Re-export the PATH before running (the setup block above handles the first invocation; subsequent calls in the same session just need the PATH re-exported):

```bash
MDP_NODE_PREFIX="${MDPOWERS_NODE_PREFIX:-${XDG_DATA_HOME:-$HOME/.local/share}/mdpowers/node}"
export PATH="$MDP_NODE_PREFIX/bin:$PATH"
node "${CLAUDE_PLUGIN_ROOT}/skills/clip/scripts/md_defuddle.js" <url> [output_path]
```

Without an output path, the script prints to stdout (useful for previewing). With a path, it writes the file and confirms.

## Output Format

Each clipped file gets YAML frontmatter followed by the article body:

```yaml
---
title: "Article Title"
source: https://example.com/article
domain: example.com
author: "Author Name"
site: "Site Name"
description: "Page meta description"
published: 2026-01-15
clipped: 2026-04-07
language: en
word_count: 1240
image: https://example.com/og-image.jpg
---

# Article Title

[clean article content...]
```

Fields are omitted when not present in page metadata. `clipped` is always today's date.

## Where to Save

If the user specifies a destination, use it. Otherwise, choose based on context:

| Context | Destination |
|---|---|
| General article or long read | `readings/web/YYYY-MM-DD_Title.md` |
| Research reference for a specific domain | `research/<domain>/references/YYYY-MM-DD_Title.md` |
| Reference for a specific project | `projects/<project>/references/YYYY-MM-DD_Title.md` |
| Quick capture, unsure where it belongs | `ops/inbox/YYYY-MM-DD_Title.md` |

All paths are relative to the user's workspace root. If the workspace has a different convention (check `CLAUDE.md` or `README.md` at the workspace root), follow that instead.

## Deriving Filenames

When the user doesn't specify a filename:

1. Prefix with today's date: `YYYY-MM-DD_`
2. Title-case the article title, replace spaces with hyphens, strip special characters
3. Truncate to ~60 characters
4. Append `.md`

Example: "How Regen Network's ecocredits work" becomes `2026-04-07_How-Regen-Networks-Ecocredits-Work.md`

## After Clipping

1. Tell the user where the file was saved and show the frontmatter summary (title, author, word count)
2. If saved to `ops/inbox/`, note it's queued for processing
3. If saved to `readings/` or `research/`, mention that `qmd update && qmd embed` can index it for search (if QMD is available)

## Handling Failures

Before working through the table below, check `references/known-hosts.md` — if the domain is listed, skip straight to the confirmed-working method.

| Symptom | Likely cause | Fix |
|---|---|---|
| `defuddle: command not found` | Not installed this session | Re-run the setup step |
| Empty or very short content | JS-rendered page (SPA) | Tell the user — Defuddle only parses static HTML |
| Garbled title or author | Bad page metadata | Clip anyway, suggest editing the frontmatter |
| Timeout after 30s | Slow or unresponsive server | Retry once, then report failure |
| Network error | Sandbox network restrictions | Check if the domain is reachable with `curl -I <url>` |
| **403 Forbidden — standard Medium** | Medium bot-blocks defuddle's user-agent | Try WebFetch on the live URL first — see fallback cascade below |
| **403 Forbidden — custom subdomain / other publisher** | Paywall or strong bot-blocking | Wayback Machine — see fallback cascade below |
| **SSRN (any URL)** | Cloudflare blocks all automated tools including WebFetch | `capture_failed: true` — SSRN cannot be accessed without a browser; library proxy is the only option |
| **410 Gone / DNS fail** | Page permanently removed | Mark index entry `[!]`, note date; do not retry |

## Fallback cascade for 403-blocked sources

When defuddle returns 403, work through the following steps in order. Stop at the first step that succeeds.

### Step 1 — Try WebFetch directly

Standard `medium.com/<publication>/<slug>` URLs respond to WebFetch even when defuddle is blocked. defuddle's user-agent triggers Medium's bot detection; WebFetch uses a different approach and retrieves the full article text verbatim.

Use the `WebFetch` tool with the original URL. If the response contains full article content (>200 words), save it with:
```yaml
captured_method: "mdpowers:clip (WebFetch — defuddle 403)"
```

**Caveat:** Custom Medium subdomains (e.g. `acme.medium.com`, `blog.example.com`) still block WebFetch. If the URL is a custom subdomain or a non-Medium publisher, skip directly to Step 2.

### Step 2 — Wayback Machine snapshot

If WebFetch also fails or returns thin content:
```bash
curl -s "https://archive.org/wayback/available?url={full-url-without-scheme}"
# e.g. medium.com/<publication>/<article-slug>
```

If `archived_snapshots.closest` exists and `status: "200"`, clip the snapshot:
```bash
defuddle parse --markdown "{wayback_url}"
```

Update frontmatter with both URLs:
```yaml
source_url: "https://original-url"
wayback_url: "https://web.archive.org/web/YYYYMMDDHHMMSS/https://original-url"
captured_method: "mdpowers:clip (Wayback Machine snapshot YYYY-MM-DD)"
```

### Step 3 — Capture failed

If all steps above fail:
```yaml
capture_failed: true
capture_notes: "defuddle 403, WebFetch blocked, no Wayback snapshot available as of {date}."
```
Mark the index entry `[?]`. Do not fabricate content.

---

## Academic paper / DOI-bearing URLs — OA API cascade

When clipping an academic paper URL that returns a paywall or 403, use this cascade to find a legal open-access version. Work through steps in order — stop at the first step that yields full text.

**Step 1 — Unpaywall (DOI → legal OA PDF)**
```bash
curl -s "https://api.unpaywall.org/v2/{DOI}?email=your@email.com"
```
Check `is_oa` and `best_oa_location.url_for_pdf`. If a PDF URL is present, download and pass to `mdpowers:convert`. Note: Unpaywall may report SSRN as an OA location but `url_for_pdf` is usually null in practice — skip if so.

**Step 2 — Semantic Scholar (OA PDF + abstract fallback)**
```bash
curl -s "https://api.semanticscholar.org/graph/v1/paper/{DOI}?fields=title,abstract,authors,year,openAccessPdf,externalIds"
```
Check `openAccessPdf.url` for a direct PDF link. Even when no PDF is available, the `abstract` field is almost always present — use it as graceful degradation. Rate limit: ~10 req/min (back off on 429).

**Step 3 — EuropePMC (life sciences / PMC mirror)**
```bash
curl -s "https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=DOI:{DOI}&format=json"
```
Check `resultList.result[0].fullTextUrlList` for a PMC full-text link.

**Step 4 — CrossRef (metadata + license + links)**
```bash
curl -s "https://api.crossref.org/works/{DOI}"
```
Check `message.link[]` for PDF URLs and `message.license[]` to confirm OA status. Useful for capturing complete bibliographic metadata even when full text is unavailable.

**Graceful degradation:** If no full text survives the cascade, capture the abstract alongside bibliographic metadata and set:
```yaml
capture_failed: true
capture_notes: "Paywalled — no OA version found. Abstract captured from Semantic Scholar. Full text requires library access."
```
A stub with abstract and metadata is more useful than an empty `capture_failed` file — it can still support in-text citation of conclusions.
