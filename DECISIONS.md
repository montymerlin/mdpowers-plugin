# Decisions — mdpowers

Architectural decisions for the mdpowers plugin, logged in a lightweight ADR (Architectural Decision Record) format. Each entry captures the context, the choice made, and its consequences — creating a searchable trail that survives memory loss.

**Format:** Each decision gets a sequential number, a status, and four sections: Context, Decision, Consequences, and (optionally) Alternatives Considered.

---

## Decision 011: Canonicalize repo instructions and add Codex install/update support

**Status:** Accepted
**Date:** 2026-04-22

**Context:** The repo's actual skill payload was already mostly host-agnostic, but the surrounding scaffold was still Claude-first. `CLAUDE.md` was the effective instruction source of truth, the install docs stopped at Claude/Cursor/Cowork, and the `clip` skill still assumed `${CLAUDE_PLUGIN_ROOT}` when locating bundled scripts. That meant the repo could honestly claim portability while still leaving a real integration gap for Codex: the skills were conceptually portable, but not cleanly installable or maintainable as global Codex skills from GitHub.

**Decision:** Make the repo's compatibility model explicit:

1. `AGENTS.md` becomes the canonical repo instruction file; `CLAUDE.md` becomes a thin compatibility wrapper.
2. `skills/` remains the canonical skill payload directory; `.claude-plugin/` remains Claude-specific packaging only.
3. Introduce `MDPOWERS_ROOT` as the portable repo-root locator, with host-specific fallbacks (`CLAUDE_PLUGIN_ROOT` for plugin hosts, `${CODEX_HOME:-$HOME/.codex}/vendor_imports/repos/mdpowers-plugin` for the default Codex vendor install path).
4. Add top-level Codex install/update scripts that clone or update the repo under the default Codex vendor path and install namespaced global skills (`mdpowers-clip`, `mdpowers-convert`, `mdpowers-transcribe`) into `~/.codex/skills/`.
5. Update current-facing docs and skill text to describe Codex as a first-class host and to prefer `AGENTS.md` over `CLAUDE.md` when reading workspace conventions.

**Consequences:**
- One canonical agent-instruction file and one canonical skill payload directory
- Codex can consume the same maintained GitHub repo rather than a hand-copied fork
- Updating Codex installs becomes a documented, repeatable `git pull` + reinstall flow
- The `mdpowers` repo stays future-friendly: hosts can differ in packaging, but not in the core skill content
- Release metadata remains plugin-oriented (`.claude-plugin/plugin.json`), so Codex support is additive rather than a second packaging system

**Alternatives Considered:**
- **Keep `CLAUDE.md` as the only instruction file** — rejected because it keeps the scaffold Claude-first even when the skills are not
- **Maintain a second Codex-only copy of the skills** — rejected because duplicated skill trees drift quickly
- **Rely on manual Codex installs with no scripts** — workable for one machine, poor as a reusable GitHub distribution pattern

---

## Decision 010: Version reconciliation and versioning convention

**Status:** Accepted
**Date:** 2026-04-21

**Context:** plugin.json said `0.3.2` while CHANGELOG.md tracked versions up to `v0.4.2` and git commit messages referenced `v0.4.1`, `v0.4`, `v0.3.2`, and `v0.3.1` — with no git tags anywhere. The cause: after the v0.4 series of changes (transcribe skill, pdf-convert removal, OA cascade, host routing), a namespace-prefix commit rolled plugin.json back to `0.3.2` without reconciling with the CHANGELOG. The result was four conflicting sources of version truth (plugin.json, CHANGELOG headings, commit messages, git tags) with no anchoring mechanism.

**Decision:** Three changes:

1. **Reconcile now:** bump plugin.json to `0.4.2` to match the CHANGELOG's latest entry, which accurately describes the current state of the plugin (transcribe skill present, pdf-convert removed, OA cascade + host routing + namespace prefix all in place).
2. **Establish convention:** add a Versioning section to CLAUDE.md that names plugin.json as the single source of truth, requires git tags on every version bump commit, and adds a pre-commit version-check (plugin.json version = latest CHANGELOG heading = commit message).
3. **Update ROADMAP:** replace stale "Publish v0.3.1 to GitHub" with "Tag and publish v0.4.2" — the first properly tagged release.

**Consequences:**
- Version is now consistent across all four sources
- Future drift is caught by the pre-commit check convention
- Git tags (once pushed) provide immutable anchors that survive rebases and commit message edits
- The convention adds one verification step to the release process — trivial overhead for significant clarity

**Alternatives Considered:**
- *Reset to v0.3.2 everywhere* — would require rewriting CHANGELOG to erase the v0.4 series, which accurately documents real changes. Rejected as revisionist.
- *Jump to v0.5.0* — would mark a clean break but misrepresents the scope of this change (it's a bookkeeping fix, not a feature release).
- *Add an automated version-check hook* — possible via a git pre-commit hook, but premature for a plugin with one contributor. The convention in CLAUDE.md is sufficient for now.

---

## Decision 009: P4 Podcast RSS as a pre-flight resolution pathway for podcast platform URLs

**Status:** Accepted
**Date:** 2026-04-15

**Context:** During the EthicHub transcription session, four podcast appearances by EthicHub founders were targeted for transcription. All four had platform-specific distribution challenges: one was Spotify-only with a dead hosting page, one was on a Buzzsprout CDN that reliably returned HTML instead of audio, and two others were on podcast platforms that required UI authentication to access episode pages. Standard approaches (yt-dlp, WebFetch on episode page, curl on page-scraped URL) all failed.

The session discovered the underlying pattern: **podcast platforms are essentially UIs on top of RSS**. Every public podcast has an RSS feed; every episode has an `<enclosure>` element with a direct audio URL. The Podcast Index API (open, free) and Apple Podcasts Lookup API (unrestricted) return RSS feeds for nearly any show. Once the RSS feed is obtained, the audio enclosure URL is a plain HTTP URL requiring no authentication — typically.

**The Buzzsprout exception:** Buzzsprout and some other CDNs use signed CloudFront URLs that expire within seconds. A naive two-step approach (get redirect URL → download separately) fails because the URL expires between the two requests. The fix: `curl -L` with browser-mimicking headers in a single command that follows all redirects before signature expiry. This pattern generalises to any podcast CDN using ephemeral signed URLs.

**Transcript checking first:** For ~20–30% of popular English-language podcasts, a transcript already exists — either via the `podcast:transcript` tag (Podcasting 2.0), Taddy's free API, or Apple Podcasts auto-generated transcripts. Checking before downloading audio is worth the few-second overhead.

**Decision:** Formalise a P4 Podcast RSS pathway with four steps:
1. Discover RSS feed (Podcast Index API → Apple Podcasts Lookup API → known CDN patterns)
2. Check for existing transcripts (podcast:transcript tag → Taddy → Apple Podcasts)
3. Download audio (standard curl → signed-CDN pattern for Buzzsprout/CloudFront)
4. Delegate to P2 (local) or P3 (API)

P4 is a pre-flight resolver, not a transcription engine. It populates richer metadata than other pathways (show title, episode number, published date, speakers from RSS) for inclusion in frontmatter.

Document in `references/pathways/P4-podcast-rss.md` (spec) and update SKILL.md routing table. No runner script yet — the pathway is currently executed manually; `scripts/podcast_rss.py` is a Near-term roadmap item.

**Consequences:**
- Podcast platform URLs now have a defined resolution path rather than failing with no guidance
- Buzzsprout CDN pattern is documented so future sessions don't diagnose it from scratch
- Transcript-first check can save 20–60+ minutes per episode for shows that publish transcripts
- P4 spec sets clear expectations about what's not supported (Spotify DRM, authenticated-only shows)
- SKILL.md routing table has a fifth row, slightly increasing decision surface — worth it for clarity

**Alternatives Considered:**
- **Document as a note in P2** — Captures the audio download fix but misses the broader podcast RSS pattern; P4 is the right abstraction level
- **yt-dlp for podcast audio** — yt-dlp can download some podcast audio from certain platforms, but it's unreliable for non-YouTube sources; the RSS enclosure approach is more universal and doesn't depend on yt-dlp's per-site extractor maintenance
- **Spotify/Apple platform-specific scrapers** — Fragile, TOS-adjacent, and unnecessary when RSS provides the same content without authentication

---

## Decision 008: OA API cascade as the standard resolution path for academic paper URLs

**Status:** Accepted
**Date:** 2026-04-15

**Context:** During an EthicHub research clipping pass, several academic papers were unreachable via standard defuddle + WebFetch because of paywalls (Sage, Elsevier), Cloudflare blocking (SSRN), and bot-blocking (Medium). The session discovered that a layered cascade of free scholarly APIs — Unpaywall, Semantic Scholar, EuropePMC, CrossRef — can recover legal full-text PDFs or at minimum useful metadata/abstracts for most closed-access papers, without needing paid library access or policy-grey tools.

Key findings from that session:
- Unpaywall reliably finds legal OA PDFs when `is_oa: true` and `url_for_pdf` is non-null
- Semantic Scholar returns abstracts for nearly all papers regardless of access status — the abstract field is an important graceful degradation
- SSRN is effectively inaccessible from all automated tools in 2026 due to Cloudflare protection; even when Unpaywall reports an SSRN OA location, `url_for_pdf` is typically null
- Medium's standard `medium.com/<publication>/<slug>` URLs respond to WebFetch even when defuddle returns 403; custom subdomains do not
- A stub file with abstract + metadata is meaningfully more useful than an empty `capture_failed: true` file — it supports in-text citation of conclusions even without full-text

**Decision:** Codify the OA API cascade as the standard resolution path in `clip/SKILL.md`:

1. Unpaywall (DOI → is_oa + url_for_pdf)
2. Semantic Scholar (openAccessPdf.url + abstract fallback)
3. EuropePMC (PMC full-text mirror, strongest for life sciences)
4. CrossRef (bibliographic metadata + license + links)

And update the 403-blocked source fallback order:
1. WebFetch (effective for standard Medium URLs; skip for custom subdomains)
2. Wayback Machine snapshot
3. capture_failed

SSRN documented explicitly as an exception: all automated access blocked, capture_failed is the correct outcome.

**Consequences:**
- Clip skill now has a documented, executable path for academic paper rescue rather than leaving it to per-session improvisation
- The "abstract as graceful degradation" tier is explicitly encouraged, making partial captures first-class instead of failures
- Medium WebFetch works around the most common 403 case without needing Wayback
- SSRN's blocking status is documented so future sessions don't waste time retrying
- Adds one new section and several rows to the clip failure handling docs — modest cognitive overhead, high practical value

**Alternatives Considered:**
- **Per-session improvisation** — the current implicit behaviour; works but doesn't accumulate learning across sessions or agents
- **Third-party aggregators (Unpaywall only)** — Unpaywall alone has a ~50% hit rate; the cascade increases this significantly for multi-venue corpora
- **Require library proxy credentials** — maximises access but requires per-institution setup; the free API cascade handles most cases without credentials
- **Sci-Hub as default step** — higher hit rate but jurisdiction-dependent legal status; added to ROADMAP as an explicit opt-in for legal contexts only

---

## Decision 007: Host routing — recommend Claude Code for complex jobs

**Status:** Accepted
**Date:** 2026-04-15

**Context:** In practice, the convert and transcribe skills perform significantly better in Claude Code than in Co-Work. The difference isn't subtle: in Co-Work, complex jobs (OCR PDFs, large documents, batch conversions, any transcription) either fail silently, degrade to lowest-quality fallbacks, or hit sandbox timeouts. The skills' graceful degradation logic was originally designed for tool-not-installed scenarios, not for the broader constraint profile of a low-RAM, no-install, short-timeout sandbox. Users running complex jobs in Co-Work were getting poor results with no clear explanation of why or what to do about it.

The specific trigger was an EthicHub research pass where a 30-page scanned PDF (60 Decibels impact assessment) required OCR. In Co-Work: pypdf extracted only bullet symbols, docling/tesseract unavailable, no brew/pip, conversion produced a near-empty stub. In Claude Code: `brew install poppler tesseract` ran in seconds, pdftoppm + tesseract extracted all 30 pages, full structured markdown produced in one pass.

**Decision:** Add a host routing check to Phase 1 of the convert skill and the transcription Probe phase. The check:
1. Detects whether the current host is Co-Work or a constrained environment (RAM < 5GB, path contains `/sessions/`, no package manager access)
2. Classifies the job as simple (fine anywhere) or complex (prefers Claude Code)
3. If constrained host + complex job: surfaces a routing recommendation with the exact Claude Code command to use
4. Always lets the user override and proceed anyway — never blocks

The routing logic lives in `skills/convert/references/environments.md` ("Host routing check" section) so both convert and transcribe reference the same definition without duplication.

**Consequences:**
- Users get an early, actionable explanation rather than a silent degraded output they don't understand
- The recommendation includes the exact command (`cd {project} && claude "Convert {filename}..."`) so the friction of switching is minimal
- Convert and transcribe skills share the routing logic via a reference, not inline copies
- The check adds ~5 lines of narration to Probe output for complex jobs — trivial overhead
- Users who want to proceed in Co-Work anyway can — the gate is advisory, not a hard block

**Alternatives Considered:**
- **Auto-degrade silently** — current behaviour, rejected because it produces poor output with no user visibility into why or how to get better results
- **Hard block in Co-Work** — rejected because sometimes a degraded output is better than nothing, and the user should have the final say
- **Separate Co-Work-specific skill versions** — rejected as maintenance overhead; one skill with adaptive routing is cleaner

---

## Decision 006: Transcribe skill architecture — modular lib + adaptive pathways

**Status:** Accepted
**Date:** 2026-04-10

**Context:** Audio/video transcription has different operational requirements across environments. Some users have local GPU capacity and prefer WhisperX + diarization for highest quality (P2); others need fast cloud-native transcription from YouTube URLs (P1); a few want to plug in custom APIs (P3 stub). A monolithic approach would either force all pathways into a single implementation (code bloat, feature conflict) or require users to choose between separate skills (/yt-transcribe, /local-transcribe) that duplicate reference material and decision-making. The transcribe skill was originally authored as a monolith in montymerlinHQ/tools/ and needed decomposition to fit the mdpowers plugin's modular conventions.

Vocabulary correction is a secondary cross-cutting concern: users accumulate domain-specific terms as they transcribe, and those terms should inform future transcriptions. The vocabulary system needed to be pluggable per pathway while keeping user vocabulary lists persistent and user-manageable.

**Decision:** Decomposed transcribe into a three-pathway architecture:

1. **P1 — YouTube fast:** native YouTube captions when available + Whisper API fallback. No local tools needed. Pathway-specific runner delegates to external services (YouTube, OpenAI).
2. **P2 — WhisperX local:** WhisperX + pyannote for diarization + speaker identification. Requires local installation and GPU/beefy CPU. Pathway-specific runner orchestrates the local tools.
3. **P3 — Cloud API service (stub):** placeholder for custom transcription APIs. Stub documents the contract; real implementations added on-demand.

All three pathways:
- Share core library modules (vocabulary cascade, speaker labeling, output formatting, quality checks)
- Use adaptive pathway selection: probe available tools at runtime, pick the best fit, allow explicit override with reasoning
- Respect XDG conventions for configuration and cached models (`$XDG_CONFIG_HOME/mdpowers/transcribe/`, `$XDG_CACHE_HOME/mdpowers/`)
- Emit host-mode metadata on each transcription so the skill can detect mismatches (e.g. P2 was selected on a host without local GPU)

Vocabulary system:
- Core lists in `skills/transcribe/references/vocabulary/standard/` (curated, version-controlled)
- User lists in `$XDG_CONFIG_HOME/mdpowers/transcribe/vocabulary/custom/` (persistent per user, auto-promoted to standard when frequency threshold is hit)
- Cascade logic: user custom → standard → generic fallback
- No API keys or model credentials stored in the skill; P1 requires upstream authentication (OpenAI API key in environment), P2 requires local models pre-downloaded

**Consequences:**
- Transcribe skill is now ~4400 lines across 15 files, significantly more code than a monolithic approach, but most bulk is library modules that future skills can reuse (speaker labeling, vocabulary cascade, quality checks)
- Pathway selection is adaptive by default, but transparent to the user (narrated in output) and overridable with explicit reasoning
- Vocabulary lists are user-managed and persistent, reducing friction for domain specialists
- Host-mode detection adds ~200 lines but enables the skill to run on any Agent SDK host without hardcoded paths
- Breaking change for anyone porting from montymerlinHQ/tools/transcribe — pathway selection is now automatic (P1 if P2 unavailable), not manual
- The P3 stub is extensible but requires per-implementation work; no built-in SaaS transcription services pre-configured

**Alternatives Considered:**

- **Monolithic single-pathway** — simplest, smallest code, but forces users into one operational model and requires separate skills for alternate pathways. Rejected as operationally inflexible.
- **Separate skills per pathway** (`/transcribe-youtube`, `/transcribe-local`, `/transcribe-api`) — maximum modularity and clarity, but duplicates reference material, vocabulary lists, and decision points across three skill artifacts. Users would have to learn three entry points and maintain three sets of docs.
- **Configuration file approach** (transcribe-config.yaml with pathway choice pre-set) — avoids runtime probing, but introduces persistent config that can go stale (e.g. "P2 is set but this host has no GPU") and requires users to think ahead instead of letting the skill adapt.
- **Inline adaptive logic (no modularity)** — smallest code, monolithic, but violates the plugin's modular philosophy and makes future pathway additions (P4: streaming, P5: custom models) harder to author and harder to test in isolation.

---

## Decision 001: Adopted agentic scaffold

**Status:** Accepted
**Date:** 2026-04-09

**Context:** The plugin was growing from a single-purpose PDF converter into a broader markdown-ingestion toolkit. Without explicit conventions, future skill authoring would drift inconsistently — each skill would make its own decisions about file layout, reference structure, frontmatter contracts, and deviation guidance. A scaffold of meta-documentation files establishes shared conventions and gives future contributors (human or agent) a clear map of how the plugin is organised.

**Decision:** Adopted the Agentic Scaffold pattern — a coordinated set of top-level files (CLAUDE.md, README.md, DECISIONS.md, ROADMAP.md, CHANGELOG.md) alongside the existing `skills/` directory. This mirrors the structure of `agentic-scaffold-plugin` and `bridging-worlds`.

**Consequences:**
- New skills follow a shared authoring convention documented in CLAUDE.md
- Structural decisions have a home (this file) rather than being buried in commits
- Future direction is visible in ROADMAP.md rather than lost in notes
- The plugin's evolution is narrated in CHANGELOG.md instead of inferred from git log
- Adds five small meta files; each serves a distinct audience

**Alternatives Considered:**
- No scaffold (README only) — worked at v0.2 scale, insufficient now that the plugin has multiple skills and an active roadmap
- Heavier framework (full ADR tooling, multiple config files) — premature
- Embed everything in README — conflates human and agent audiences, README becomes unmaintainable

---

## Decision 002: Replaced pdf-convert with adaptive convert skill

**Status:** Accepted
**Date:** 2026-04-09

**Context:** The original `pdf-convert` skill was docling-first and assumed a Claude Code + macOS environment with ample RAM. In low-RAM environments (e.g. the Cowork sandbox with ~3.8GB, or small CI runners), docling is SIGKILL'd on any real PDF due to OOM. The skill also had no semantic enrichment — it produced plain text extraction without structured representations of diagrams, comparisons, or visual content. A real-world test on the Kwaxala Overview 2026 pitch deck made both limitations painfully visible: the skill couldn't run at all in the available environment, and even when fallback extraction succeeded, the output was a flat text dump that an AI couldn't meaningfully reason over.

Beyond PDFs specifically, users also wanted consistent treatment for docx, pptx, epub, and other document types. Writing a separate skill per format would fragment the plugin and duplicate effort.

**Decision:** Replaced `pdf-convert` with a new `convert` skill that:

1. Handles any document type (PDF, docx, pptx, epub, html, image) through a single entry point
2. Probes the source and environment at runtime, matching the source to one of seven recipe archetypes and picking a viable engine from an ordered preference list
3. Follows a five-phase workflow (Probe → Plan → Execute → Enrich → Verify) with adaptive planning budget (tight / standard / deep)
4. Delegates to built-in Anthropic skills (`pdf`, `docx`, `pptx`, `xlsx`) as first-choice engines, with graceful degradation to pymupdf, pandoc, and other universal fallbacks
5. Applies six enrichment playbooks (diagrams→mermaid, comparisons→tables, images, descriptions, frontmatter, glossary) tuned per recipe
6. Operates under a "guides not rails" principle — recipes and playbooks are defaults, deviation is a normal move, transparency is the safety valve

`pdf-convert` is kept on disk with a deprecation notice and will be removed in v0.4, giving users one release cycle to migrate.

**Consequences:**
- The plugin now handles a much broader input surface (not just PDFs)
- Environment-specific failures become graceful degradations instead of hard blocks
- Output quality is dramatically better for complex sources (slide decks, institutional reports, books)
- The plugin now has a documented authoring convention that future skills can follow
- Maintenance burden: the convert skill is ~1,900 lines across 12 files — significantly more than pdf-convert's ~200 lines, but most of that is reusable catalogue content
- Users need to update muscle memory from `/pdf-convert` to `/convert`

**Alternatives Considered:**

- **Fix pdf-convert in place** — smaller change, but wouldn't address the enrichment gap, the multi-format need, or the underlying architectural mismatch between "assume docling works" and the realities of constrained environments (low-RAM sandboxes, CI runners, hosts without docling at all)
- **Build a multi-skill suite** (`convert-plan`, `convert-execute`, `convert-verify`) — more modular but fragmented for no current benefit; folded the phase structure inside a single skill as internal stages, with the option to split later if usage demands it
- **Thin router skill** — smallest change, all intelligence in prose instructions the agent reads each time. Rejected because it provided no mechanism for the adaptive planning budget and no place for the enrichment playbooks to live

---

## Decision 003: "Guides not rails" as project-wide principle

**Status:** Accepted
**Date:** 2026-04-09

**Context:** During the design of the `convert` skill, a tension emerged between prescriptive instructions (catalogue-driven, deterministic, easy to verify) and adaptive judgment (agent-driven, context-sensitive, harder to verify but often producing better output). Over-prescription had been a failure mode of `pdf-convert` — it assumed a specific engine and failed when that assumption was wrong. Under-prescription would risk chaos, with every invocation producing inconsistent results.

**Decision:** Established "guides not rails" as a project-wide design principle. Recipes, playbooks, and phase instructions are defaults the agent can adapt from when a specific document warrants it. Deviations must be named in the agent's narration ("treating this as X but skipping Y because Z"). Hard rails are listed explicitly in `skills/convert/references/anti-patterns.md` — everything else is soft.

The principle applies to all future skills in the plugin, not just `convert`.

**Consequences:**
- Recipes can capture good defaults without becoming bureaucratic
- Agents are trusted to make judgment calls, with transparency as the accountability mechanism
- Future skill authors must explicitly document which rails are hard and which are soft
- Verification is outcome-based (success criteria) not process-based (did you follow the steps)

**Alternatives Considered:**
- **Fully prescriptive** (every step mandatory) — simpler to verify, but brittle in exactly the way pdf-convert was brittle
- **Fully adaptive** (no catalogue) — each conversion starts from scratch; wastes effort and produces inconsistent results

---

## Decision 004: Prefer built-in Anthropic skills as first-choice engines

**Status:** Accepted
**Date:** 2026-04-09

**Context:** Anthropic ships built-in skills for PDF, docx, pptx, and xlsx handling. These are maintained by the people who trained the model and receive updates tied to the model's capabilities. Writing custom extractors duplicates effort and produces tools that inevitably fall behind the built-ins. At the same time, the built-ins don't cover every environment (they may not be available in all contexts) and don't handle every edge case (specialised enrichment, recipe-specific output shapes).

**Decision:** The `convert` skill (and any future mdpowers skills handling document formats) will prefer built-in Anthropic skills as the first-choice engine in their preference lists. Custom or third-party tools (docling, marker, pymupdf, pandoc) are fallbacks used when the built-in isn't available or doesn't meet the recipe's needs.

**Consequences:**
- Less duplicated effort — mdpowers focuses on orchestration, enrichment, and recipes rather than re-implementing extraction
- Output benefits from ongoing Anthropic maintenance of the built-in skills
- The plugin is lighter-weight and easier to maintain
- Graceful degradation path is still necessary for environments without the built-ins

**Alternatives Considered:**
- **Custom-first** — maximum control, but loses the benefit of maintained tools and duplicates work
- **Built-in-only** — simpler but breaks in environments without the built-ins, and doesn't handle edge cases that need custom enrichment

---

## Decision 005: Rename to `mdpowers` and decouple from Cowork branding

**Status:** Accepted
**Date:** 2026-04-09

**Context:** The plugin was originally named `mdpowers-cowork` and the README described it as "A Claude Cowork plugin". In practice, the plugin follows the standard Claude Agent SDK plugin contract (`.claude-plugin/plugin.json` + `skills/<name>/SKILL.md`) and has no runtime dependency on Cowork — it can load in Claude Code, Cursor (via MCP), the Claude desktop app, or any custom Agent SDK host. The "-cowork" suffix and the README framing were misleading: they signalled "this only works in Cowork" when the plugin was actually host-agnostic by construction.

A real portability bug made this concrete. The `clip` skill had three hardcoded references to a stale Cowork session slug (`/sessions/cool-exciting-euler/.local/`). These paths were broken even within Cowork (each session has a different slug) and guaranteed to fail anywhere else. The bug had survived because nobody had tested the plugin outside the environment where it was originally authored — which itself was a symptom of the branding signalling that Cowork was the only target.

Separately, the repository URL in `plugin.json` pointed at `github.com/montymerlin/mdpowers-cowork`, which was never the actual repo name — the real repo is `github.com/montymerlin/mdpowers-plugin`. This was a copy-paste error from an earlier version of the manifest that had gone unnoticed.

**Decision:** Rename the plugin from `mdpowers-cowork` to `mdpowers` and explicitly decouple it from Cowork branding. Specifically:

1. **Plugin name** in `plugin.json`: `mdpowers-cowork` → `mdpowers`. This changes the skill namespace from `mdpowers-cowork:clip` to `mdpowers:clip`.
2. **Repository URL** in `plugin.json`: fix to `github.com/montymerlin/mdpowers-plugin` (the real value).
3. **Version bump** to 0.3.1 (technically a breaking change for anyone importing `mdpowers-cowork:...`, but the plugin has no known external users yet).
4. **Fix the clip hardcoded paths bug**: replace the stale session-slug paths with a portable install bootstrap using `$MDPOWERS_NODE_PREFIX` (defaulting to `$XDG_DATA_HOME/mdpowers/node` or `$HOME/.local/share/mdpowers/node`).
5. **Add a new top-level file, COMPATIBILITY.md**, documenting the supported-host matrix, runtime contract, per-host quirks, and portability testing procedure. This lets CLAUDE.md stay focused on conventions and agent boundaries without getting clogged with environment details.
6. **Sweep the docs** to remove Cowork-as-primary framing: README, CLAUDE.md, DECISIONS.md, ROADMAP.md, and CHANGELOG.md all get their titles and intros updated. The `convert` skill references get the same treatment — Cowork becomes one example of a constrained environment, not the motivating case.
7. **Add an 8th design principle**: "Host-agnostic by construction — no hardcoded paths, no assumed tools, no branding to a specific host." This crystallises the lesson from this decision into a rule future skill authors can't easily miss.

**Consequences:**
- Users in Claude Code, Cursor, and other Agent SDK hosts can now install and use the plugin without the documentation confusing them about whether it'll work
- The `clip` skill is actually portable (was broken even in Cowork before this fix)
- Future skill authors have an explicit "no hardcoded paths" rule to follow
- Breaking change: anyone importing `mdpowers-cowork:...` must update to `mdpowers:...` (no known external users as of this rename, so impact is limited)
- The GitHub repo name stays as `mdpowers-plugin` — no repo rename needed, just a manifest fix
- COMPATIBILITY.md becomes the first place to look for portability questions, reducing churn in CLAUDE.md

**Alternatives Considered:**

- **Keep the name, just fix the docs** — conservative, no breaking change, but keeps the misleading `mdpowers-cowork:...` skill namespace and doesn't signal the shift in positioning
- **Rename the GitHub repo too** (`mdpowers-plugin` → `mdpowers`) — cleaner, but adds a redirect that everyone has to update, and the current name is fine
- **Skip COMPATIBILITY.md and put everything in CLAUDE.md** — simpler (one less file), but CLAUDE.md is already ~150 lines and was going to bloat further; separating host-specific details into a dedicated file keeps both documents focused
- **Add the host-agnostic principle without renaming** — would leave the misleading name in place while claiming the plugin is host-agnostic; internally inconsistent

---

<!-- Scaffold sources: Michael Nygard ADR proposal (2011), Keeling & Runde sustainable ADRs (IEEE Software), agentic-scaffold-plugin v0.1.0 -->
