# Anti-patterns — the hard rails

The `convert` skill operates on the "guides not rails" principle: most defaults are adjustable, and deviation is a normal move. This file lists the few things that are **hard rails** — non-negotiable rules that should never be violated, regardless of context.

If you catch yourself doing one of these, stop and reconsider.

## Hard rails

### 1. Verify always runs

Every conversion, regardless of recipe or budget, must run the Verify phase. Tight budget compresses Plan into a sentence, but Verify still runs. You do not skip Verify to "save time" or because the document "looked fine."

**Why:** Verify is the only mechanical check that catches broken asset references, missing frontmatter, and corrupted output. A converted file that wasn't verified is not a trustworthy deliverable.

### 2. Required frontmatter fields are non-negotiable

The required fields listed in P5 (`title`, `source_file`, `source_type`, `recipe`, `extracted_via`, `converted_on`, `quality`) must be populated on every output. If a field can't be determined, write `unknown` explicitly — never blank, never null, never omit.

**Why:** Downstream tooling (indexers, search, static site generators, Notion sync) assumes these fields exist. Missing fields break pipelines silently.

### 3. Asset references must resolve

Every image/link reference in the markdown must point to a file that actually exists on disk. Verify checks this.

**Why:** Broken references are silent failures — they look fine in rendered markdown until someone actually tries to open the asset.

### 4. Never silently produce OCR garbage

For scanned documents where OCR fails or confidence is low, the markdown body must explicitly say so. Do not bury a failed OCR under a thin layer of apparent content.

**Why:** An agent reading "clean" markdown assumes it's faithful to the source. OCR garbage that passes as content is actively misleading.

### 5. Never use absolute file paths in output

All asset references in the markdown must be relative. Absolute paths (`/Users/monty/...`, `/home/user/...`) break portability instantly.

**Why:** Converted files move between environments (Claude Code, Cursor, Cowork sandbox, git repos, Notion, CI runners). Absolute paths only work in the environment that created them.

### 6. Never skip degradation recording

When a conversion falls back from a preferred engine to a lower-quality one, the frontmatter must record `quality: degraded` with `quality_notes`. Silently pretending a degraded conversion is full quality is misleading.

**Why:** Downstream re-conversion decisions depend on this signal. A file marked `quality: full` won't be re-converted; a file that should have been marked `degraded` gets stuck at lower quality forever.

### 7. Never invent metadata

If a DOI, ISBN, author name, publication year, or other metadata field can't be determined from the source, do not make it up. `"unknown"` or `"none"` is always the correct answer.

**Why:** Invented metadata poisons the knowledge base. One fabricated DOI is worse than a thousand "unknown" values.

### 8. Never fabricate or embellish source content

`convert` extracts and structures; it does not generate. Do not add paragraphs, sentences, or bullet points that weren't in the source. Do not "improve" the source's prose, fix its logic, or fill in implied content.

**Why:** The whole point of conversion is faithful representation. Fabrication defeats the purpose.

Exception: semantic descriptions (P4) and prose around structured representations (P1, P2) are interpretive — you are describing the source, not extending it. That's allowed. But never invent *content* as if it were in the source.

### 9. Never auto-commit in a git repo

If the working directory is a git repository, never run `git commit` or `git add && commit` after conversion. Show the diff, let the user decide.

**Why:** Bridging Worlds' AGENTS.md explicitly forbids auto-commit, and it's a sensible default for any repo. Auto-committing generated content is how repositories get polluted.

### 10. Never skip the commons-awareness announcement

If `AGENTS.md` or `CLAUDE.md` is detected in the working tree and commons conventions are being applied, name them at the start of your response. Don't silently reshape output based on detected conventions.

**Why:** Silent reshaping surprises users. Transparency is the safety valve — the user should see why their output looks different from default.

## Soft rails (the usual suspects — negotiable)

For completeness, these are things people sometimes think are hard rails but aren't:

- ❌ "Must use mermaid for all diagrams" — soft, use bullets or tables when mermaid fights the content
- ❌ "Must produce exactly the recipe's output shape" — soft, adapt when the document warrants
- ❌ "Must use the highest-preference engine available" — soft, skip if it's known to fail on this source
- ❌ "Must ask the user before doing anything" — soft, tight budget proceeds silently
- ❌ "Must produce a plan artifact" — soft, only in deep budget

If in doubt whether something is a hard rail or a soft one: it's a hard rail only if it's in this file.

## What to do when a hard rail fails

If you genuinely cannot satisfy a hard rail (e.g. the source has no title anywhere and you need to populate `title`), the correct response is:

1. **Stop and say so.** Don't fudge it.
2. **Explain what you tried.** List the places you looked for the data.
3. **Offer alternatives.** "I can use the filename as title, or you can provide one, or we can set it to `unknown`."
4. **Wait for user direction.**

Hard rails exist because violating them silently produces long-term damage. Stopping loudly is almost always the right call.
