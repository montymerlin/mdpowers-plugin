# Changelog — mdpowers

A narrative record of how this plugin evolves. Updated after significant work sessions, not per-commit. Focuses on the "why" and "what changed" rather than granular diffs.

---

## 2026-04-27 — Plugin audit pass + skill name fix

Audited the plugin against `/create-cowork-plugin` standards. Fixed the namespaced skill `name:` frontmatter bug across all 3 SKILL.md files (`mdpowers:clip` → `clip`, etc.). Expanded `.gitignore` from minimal (5 patterns) to full portfolio template covering `_dist/`, `*.plugin`, `node_modules/`, `.venv/`, editor noise, worktrees.

AGENTS.md Repo map updated to include `SETUP.md` (mark COMPATIBILITY.md as stub) and `.gitignore`; added the canonical "Packaging for Cowork" section. SETUP.md got the "Quick Install (for AI agents)" decision tree (with required-dependency check for Python 3.10+ and Node 18+ before any install path runs), Cowork 3-option packaging pattern, and global-vs-local Claude Code install split.

Fixed README.md stale references: Project Structure was missing SETUP.md and `.gitignore`, and listed COMPATIBILITY.md as a real doc (it's a stub now); Contributing step 6 was directing portability changes to COMPATIBILITY.md (now points at SETUP.md as the canonical reference). **Flagged for local cleanup** (perm-locked from session): `__pycache__/` directories at `skills/transcribe/scripts/{,lib/}` are tracked despite being in `.gitignore` — needs `git rm -r --cached`.

## 2026-04-27 — Cowork packaging: SETUP.md replaces COMPATIBILITY.md

Folded the host-compatibility and runtime-contract content from `COMPATIBILITY.md` into a new `SETUP.md` that follows the workspace-wide setup-canon pattern. `COMPATIBILITY.md` is now a one-line stub redirecting to SETUP.md (preserves any external links). `README.md`'s install section was trimmed to a pointer. The plugin is now packaged as `mdpowers-0.4.3.plugin` in `ops/plugins/_dist/` using the new `cowork-plugin-packager` skill. No conversion-engine or skill changes.

## 2026-04-23 — Clarified grounding benefits and markdown tradeoffs

Refined the README and compatibility docs to make a more honest claim about why markdown conversion helps in agent workflows. The docs now say explicitly that clean markdown or structured text often improves retrieval, chunking, citation, and synthesis, which can reduce hallucination risk indirectly by improving grounding. They also now spell out the tradeoffs that were previously too implicit: conversion takes time, interactive prep can consume tokens, OCR can introduce errors, and markdown can lose layout or visual information that still matters for scans, forms, dense tables, and highly designed PDFs. This makes the repo's positioning more nuanced and more credible for people using `mdpowers` in serious research or document-heavy workflows.

## 2026-04-22 — v0.4.3: AGENTS.md canon + Codex global install path

Made the repo scaffold match the portability story the skills were already trying to tell. `AGENTS.md` is now the canonical instruction file and `CLAUDE.md` has been reduced to a compatibility wrapper, which brings the repo in line with the broader compatibility-layer pattern used elsewhere in montymerlinHQ. More importantly, Codex is now treated as a first-class host rather than an afterthought: the docs explain the difference between Claude plugin packaging and Codex global skills, the skills use a portable `MDPOWERS_ROOT` resolution convention instead of assuming `${CLAUDE_PLUGIN_ROOT}`, and two new scripts (`scripts/install_codex_skills.sh`, `scripts/update_codex_skills.sh`) establish a repeatable GitHub-backed install/update flow via `~/.codex/vendor_imports/repos/mdpowers-plugin`. Current-facing skill text and compatibility docs were swept so workspace conventions prefer `AGENTS.md`, and host guidance now talks about full local terminal hosts rather than only Claude Code where the distinction matters. This is a compatibility release, not a methodology rewrite, so it lands as v0.4.3.

## 2026-04-21 — v0.4.2: version reconciliation + marketplace.json fix

Fixed marketplace.json version (was still 0.3.2, now 0.4.2 to match plugin.json). Added marketplace.json to the directory structure listing in CLAUDE.md.

Reconciled version drift between plugin.json (which said 0.3.2), CHANGELOG (which said v0.4.2), and git commit messages (which mentioned v0.3.1 through v0.4.1 with no tags). The cause: the v0.3.2 namespace-prefix commit rolled plugin.json back without reconciling with the CHANGELOG's v0.4 series. plugin.json now correctly reads 0.4.2, matching the CHANGELOG.

Added a versioning convention to CLAUDE.md establishing plugin.json as the single source of truth, requiring git tags on every version bump, and adding a pre-commit version-check (plugin.json version = latest CHANGELOG heading = commit message). This prevents the drift pattern that caused the inconsistency. Updated ROADMAP to replace the stale "Publish v0.3.1" item with "Tag and publish v0.4.2." See Decision 010.

---

## 2026-04-15 — v0.4.1 (continued): podcast transcription learnings from EthicHub session

A follow-on pass to the same EthicHub research session that produced v0.4.1. The clip skill was fixed in the morning; the transcription session ran in the afternoon and produced its own set of learnings.

**P4 Podcast RSS pathway documented.** Four EthicHub founder podcast appearances needed transcription but had Spotify-only distribution or dead hosting page links. The solution: podcast platforms are just UIs on top of RSS. Every show has a feed; every episode has an enclosure URL; the audio is almost always publicly accessible. A new pathway — P4 (Podcast RSS) — codifies the four-step resolution flow: (1) discover RSS feed via Podcast Index API or Apple Podcasts Lookup API, (2) check for existing transcripts (`podcast:transcript` tag, Taddy, Apple Podcasts), (3) download audio (handling signed CDN patterns), (4) delegate to P2 for transcription. The full spec is in `references/pathways/P4-podcast-rss.md` and the routing table in SKILL.md.

**Buzzsprout signed CDN pattern.** Direct `curl` of Buzzsprout episode URLs returns HTML instead of audio. Root cause: signed CloudFront URLs expire within seconds; a two-step download fails because the signature window closes before the second request. Fix: single `curl -L` with browser-mimicking headers (`User-Agent`, `Referer`, `Accept`) that follows all redirects in one TCP session. This pattern is documented in both P2 (failure modes) and P4 (Step 3) and generalises to any podcast CDN using ephemeral signed URLs.

**PyTorch 2.6 two-patch fix.** The existing runner had Patch 2 (force `weights_only=False` in `lightning_fabric`) but lacked Patch 1 (register `omegaconf.ListConfig` / `DictConfig` as safe globals). Applying only one patch still failed. Both patches are now in `scripts/whisperx_local.py` and documented with discovery context in P2's failure modes section.

**Python 3.9 `Optional[dict]` fix.** `lib/errors.py` used `dict | None` union syntax introduced in Python 3.10. The `.venv-whisperx` environment uses Python 3.9, causing the runner to fail on import. Fixed by adding `from typing import Optional` and changing `dict | None` → `Optional[dict]`. Caught because this is exactly the kind of syntax drift that breaks on older Python without a CI matrix.

No breaking changes. SKILL.md routing table updated. ROADMAP.md updated with P4 runner as a Near-term item.

---

## 2026-04-15 — v0.4.1: source resolution learnings from EthicHub research pass

A research clipping pass for the Bridging Worlds EthicHub case study required capturing 14+ sources across a mix of Medium blog posts, academic papers (Sage, Elsevier, NBER), and grey-literature URLs. The session hit every meaningful failure mode the `clip` skill could encounter — and the learnings are now codified.

**The 403 fallback cascade is now correct.** The previous docs sent every 403 straight to the Wayback Machine. The session found that standard `medium.com/<publication>/<slug>` URLs respond to WebFetch even when defuddle is blocked — because defuddle's user-agent triggers Medium's bot detection while WebFetch does not. The correct cascade is: WebFetch first → Wayback if WebFetch fails → capture_failed if both fail. Custom Medium subdomains (e.g. `dacxi.medium.com`) still block WebFetch and go straight to Wayback. This is now documented in the skill with explicit handling for both cases.

**SSRN is effectively inaccessible in 2026.** Cloudflare blocks defuddle, WebFetch, curl with browser UA, and any other automated tool. Even when Unpaywall reports SSRN as an OA location, `url_for_pdf` is typically null. SSRN is now listed explicitly in the Handling Failures table with the correct guidance: `capture_failed: true`, library proxy is the only option.

**OA API cascade for academic papers.** The session established a four-step cascade — Unpaywall → Semantic Scholar → EuropePMC → CrossRef — that recovers legal full-text PDFs or metadata/abstracts for most paywalled academic papers without library access. Semantic Scholar in particular returns abstracts for nearly all papers regardless of access status, which enables a useful new pattern: abstract-as-graceful-degradation. A `capture_failed: true` file with a well-captured abstract and full bibliographic metadata is meaningfully more useful than an empty stub — it can still support in-text citation of conclusions even when full text is unavailable. This pattern is now documented explicitly in the clip skill.

**Sci-Hub added to roadmap as a parked idea.** For legal-context use cases (researchers in permissive jurisdictions, or papers already in personal possession), a Sci-Hub lookup step in the OA cascade would significantly increase full-text hit rates. This requires explicit user opt-in and jurisdiction awareness. Added to ROADMAP as `parked` with a clear note on the legal considerations.

**New ADR: D008.** The OA API cascade is logged as an architectural decision, documenting the cascade order, the SSRN exception, the abstract-tier insight, and the Sci-Hub reasoning.

No breaking changes. The clip skill's behaviour is backward-compatible — the new cascade extends the failure handling docs rather than changing the primary flow.

---

## 2026-04-10 — v0.4: `transcribe` skill + `pdf-convert` removal

Removed the deprecated `pdf-convert` skill after one release cycle of deprecation (deprecated in v0.3, scheduled for removal in v0.4). Its knowledge bank (19 known issues from 16 reference PDFs) and helper scripts (`pdf_postprocess.py`, `pdf_verify.py`) were migrated to `skills/convert/references/` so the `convert` skill can still reference them.

Added the `transcribe` skill for converting audio and video to structured, speaker-labelled markdown with adaptive vocabulary correction. The skill is decomposed into library modules and runners, supporting three pathways: P1 (YouTube native + Whisper API fallback, fast), P2 (WhisperX + pyannote diarization, local + high-quality), and P3 (cloud API services, stub). Vocabulary cascade uses XDG conventions for user-extensible word lists, with adaptive promotion from `custom/` to `standard/` based on frequency. Host-mode detection enables portable operation across Claude Code, Cursor, and Cowork without hardcoded paths. Implementation spans ~4400 lines of Python across 15 files (lib modules, runners, CLI entry points) plus 10 reference documents (environment setup, playbooks, anti-patterns, P1/P2/P3 pathway details, vocabulary handling, speaker identification, output format).

The skill follows the "guides not rails" principle established in the plugin's core design: pathway selection is adaptive (probes available tools and chooses the best fit), but agents can override with explicit reasoning. Per-pathway success criteria and failure modes are documented in the reference playbooks. No hardcoded session slugs or assumed tools — everything probes at runtime.

---

## 2026-04-09 — v0.3.1: portability pass and rename to `mdpowers`

Follow-up release on the same day as v0.3. This one was motivated by a simple observation from the user: the README still described the plugin as "A Claude Cowork plugin" even though the Agent SDK plugin contract is host-agnostic by construction. The framing was signalling "this only works in Cowork" when the plugin should work in Claude Code, Cursor (via MCP), the Claude desktop app, and any other host that loads Agent SDK plugins.

An audit turned up one real portability bug alongside the branding drift. The `clip` skill had three hardcoded references to a stale Cowork session slug (`/sessions/cool-exciting-euler/.local/`) from the session it was originally authored in. These paths were broken even within Cowork — each session has a different slug — and guaranteed to fail in any other host. The bug had survived because nobody had tested the plugin outside the environment where it was written, which was itself a symptom of the Cowork-centric framing.

The fix was a full rename and a portability pass:

- **Plugin name:** `mdpowers-cowork` → `mdpowers`. Skill namespace becomes `mdpowers:clip`, `mdpowers:convert`, etc.
- **Repository URL** in `plugin.json`: fixed to `github.com/montymerlin/mdpowers-plugin` (was pointing at a nonexistent `mdpowers-cowork` repo — an old copy-paste error from the v0.2 manifest).
- **Clip install bootstrap** rewritten to use `$MDPOWERS_NODE_PREFIX` (defaulting to `$XDG_DATA_HOME/mdpowers/node` or `$HOME/.local/share/mdpowers/node`). No more hardcoded session slugs. Set the env var to override if the default isn't writable.
- **New file: COMPATIBILITY.md** at the plugin root. Documents the supported-host matrix (Claude Code, Cursor, desktop app Cowork mode, custom Agent SDK hosts, direct API), the runtime contract (Python 3.10+, Node 18+, writable home), per-host quirks (low-RAM docling OOM, hosts without built-in skills, read-only homes), and a portability testing procedure. This keeps CLAUDE.md focused on conventions without getting clogged with environment details.
- **Doc sweep across CLAUDE.md, README.md, DECISIONS.md, ROADMAP.md, CHANGELOG.md** — titles updated, Cowork-as-primary framing removed, install section added to README covering all supported hosts, repo URL corrected everywhere. The `convert` skill references now treat Cowork as one example of a constrained environment rather than the motivating case.
- **New design principle #8:** "Host-agnostic by construction — no hardcoded paths, no assumed tools, no branding to a specific host." Added to CLAUDE.md and README.md so future skill authors can't easily miss it.

One new ADR logged: **D005 (rename to `mdpowers` and decouple from Cowork branding)**, which documents the branding drift, the portability bug, the fix, and the alternatives considered (including keeping the name and just fixing the docs, which was rejected as internally inconsistent).

Breaking change for any external users importing `mdpowers-cowork:...` skills — they'll need to update to `mdpowers:...`. The plugin has no known external users yet, so the impact is limited. The GitHub repo name stays as `mdpowers-plugin`; no repo rename needed, just a manifest fix.

**Next:** a proper portability test matrix across at least three hosts (Claude Code, Cursor, Cowork), documented in COMPATIBILITY.md with a "Tested on:" line in the README. Added to the roadmap.

---

## 2026-04-09 — v0.3: the `convert` skill and the agentic scaffold

Major release. Two big changes landed together.

**The `convert` skill replaces `pdf-convert`.** A real-world test converting the Kwaxala Overview 2026 pitch deck exposed several fundamental problems with the old `pdf-convert` skill. First, it was docling-first and docling OOMs in low-RAM environments (the Cowork sandbox with ~3.8GB was the specific motivating case), so the skill couldn't actually run on constrained hosts. Second, it only handled PDFs — users wanted consistent treatment for docx, pptx, and other formats. Third, it produced flat text extraction with no semantic enrichment, meaning the output was technically markdown but not meaningfully navigable or AI-readable. A 25-slide pitch deck full of flowcharts and layered stack diagrams came out as 25 pages of loose captions with no structure.

The redesign started with a superpowers-style brainstorming session that went through six chunks of design decisions with explicit approval gates. The chosen architecture is an adaptive orchestrator: five phases (Probe → Plan → Execute → Enrich → Verify), seven recipe archetypes, six enrichment playbooks, and a three-tier planning budget (tight / standard / deep) that scales ceremony to document complexity. Simple one-pagers get tight treatment with no ceremony; novel or complex documents get a plan artifact and user review before execution. The key design principle — "guides not rails" — was named explicitly after the user pointed out that over-prescription can itself be a failure mode.

The new skill delegates to built-in Anthropic skills (`pdf`, `docx`, `pptx`, `xlsx`) as first-choice engines wherever possible, with ordered fallback to docling, marker, pymupdf, and pandoc. Graceful degradation is the default: when a preferred engine isn't available, the skill drops silently to the next one and records `quality: degraded` in the output frontmatter so downstream work can find and re-convert those files later.

Seven recipes: `slide-deck-visual`, `academic-paper`, `institutional-report`, `book-longform`, `scanned-document`, `simple-onepager`, `hybrid-novel`. Each declares its own triggers, engine preferences, enrichment playbook IDs, output shape, and success criteria. The `hybrid-novel` catch-all always escalates to deep planning, which means genuinely unfamiliar source types get a proper plan written before execution instead of a best-guess attempt.

Six playbooks in `skills/convert/references/enrichment/`: P1 diagrams-to-structured (the Kwaxala lesson — image + description + mermaid), P2 comparisons-to-tables, P3 images-and-assets, P4 semantic-descriptions, P5 frontmatter-and-metadata, P6 cross-references-and-glossary. Each is a short document (50–230 lines) with a worked example, deviation guidance, and explicit failure modes. P1 and P5 are the load-bearing ones and are written in full detail.

`pdf-convert` is deprecated in place with a notice at the top of its SKILL.md pointing users at `convert`. It stays on disk for one release cycle (removed in v0.4) to preserve existing muscle memory. The helper scripts (`pdf_postprocess.py`, `pdf_verify.py`) remain available and will be merged into `convert/references/` when `pdf-convert` is removed.

**Adopted the agentic scaffold.** Simultaneously added the top-level scaffold files matching the `agentic-scaffold-plugin` architecture: CLAUDE.md (agent instructions, conventions, boundaries), DECISIONS.md (ADR-style decision log with four initial entries documenting this session's choices), ROADMAP.md (near-term / future / parking-lot / decided), and this CHANGELOG.md. README.md was updated to match the new structure and reflect the new skill.

The scaffold adoption was motivated by the plugin's growth from a single-purpose PDF converter into a broader ingestion toolkit. Without explicit conventions, future skill authoring would drift inconsistently. The scaffold gives future contributors (human or agent) a clear map of how the plugin is organised and documents the design principles that should inform new skills.

Four decisions are logged in DECISIONS.md for this release: D001 (agentic scaffold adoption), D002 (convert replaces pdf-convert), D003 ("guides not rails" as project-wide principle), D004 (built-in Anthropic skills preferred as first-choice engines).

Design spec and staging README for this release are preserved in `bridging-worlds/labs/mdpowers-v2-convert/` for historical reference.

**Next:** validate the new skill against 3-5 real documents of different archetypes, tune recipes based on observed gaps, then publish the v0.3 release tag. See ROADMAP.md for details.

---

## 2025-11-ish — v0.2: clip + pdf-convert

Initial public release. Two skills: `/clip` for web-page-to-markdown via Defuddle, and `/pdf-convert` for PDF-to-markdown via Docling with automated post-processing. Both use lazy dependency installation (~2s for defuddle, ~30-60s for docling) so nothing installs at plugin load time.

`/clip` produces markdown with YAML frontmatter (title, source, author, date, word count). `/pdf-convert` produces markdown with referenced images, automated post-processing for common extraction artifacts (ligatures, glyph IDs, heading detection), and an LLM-based quality review pass.

Tested extensively in Claude Code on macOS with a reference corpus of 16 PDFs. Known issues catalogued in `skills/pdf-convert/references/knowledge-bank.md`.

<!-- Scaffold sources: keep-a-changelog (adapted to narrative style), bridging-worlds narrative changelog pattern, agentic-scaffold-plugin v0.1.0 -->
