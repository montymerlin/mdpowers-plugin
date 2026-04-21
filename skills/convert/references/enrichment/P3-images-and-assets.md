# P3 — Images and assets

Standard treatment for images, photos, figures, and page renders. This playbook covers format selection, resolution, folder layout, alt text, and reference conventions.

## Output format by image type

| Image type | Format | Rationale |
|---|---|---|
| Photo / natural image | JPEG q82 | Small size, acceptable quality |
| Slide render (full page) | JPEG q82 at 144dpi | Optimal balance — ~200KB per slide |
| Diagram with text | PNG | Text stays sharp |
| SVG in source | SVG passthrough | Don't rasterise vectors |
| Screenshot | PNG | Often has text/UI elements |
| Academic figure (chart/plot) | PNG at 200dpi | Preserves precision |
| Scanned page | JPEG q85 | Photos of paper are essentially photos |

## Resolution defaults

- **Slide decks**: 144dpi. Higher than 144 bloats file size; lower loses readability of in-slide text.
- **Academic figures**: 200dpi. Preserves chart precision.
- **Photo-heavy reports**: 96dpi. No one zooms in on illustrative photos.
- **Scanned pages**: 150dpi. Enough for OCR verification but not excessive.

Override defaults when the source quality justifies it (a low-quality source shouldn't be rendered at high DPI — you're just upscaling noise).

## Folder layout

Per-document asset subfolders:

```
<doc-slug>.md
<doc-slug>-assets/           # for mixed asset types
  fig-01-caption-slug.png
  fig-02-caption-slug.png
  table-01-caption-slug.png
```

For slide decks, use a more specific subfolder name:

```
<deck-slug>.md
<deck-slug>-slides/          # slide-specific naming
  slide-01.jpg
  slide-02.jpg
```

For books with per-chapter splits, use a shared asset folder at the book level:

```
<book-slug>/
  index.md
  01-chapter.md
  assets/                    # shared across chapters
    ch01-fig-01.png
```

## Filename conventions

- **Slides**: `slide-NN.jpg` where NN is zero-padded
- **Figures**: `fig-NN-<short-slug>.png` where slug is derived from the caption
- **Tables extracted as images**: `table-NN-<short-slug>.png`
- **Page renders (scanned docs)**: `page-NN.jpg`
- Always zero-pad numbers for correct sort order (`slide-01`, not `slide-1`)

## Alt text

Every image reference must have alt text. Short + descriptive, not decorative.

**Good:**
- `![Slide 9: The Kwaxala four-layer stack](./slides/slide-09.jpg)`
- `![Figure 3: Monthly offset credit issuance, 2014-2024](./assets/fig-03-monthly-issuance.png)`

**Bad:**
- `![](./slides/slide-09.jpg)` — no alt text
- `![image](./slides/slide-09.jpg)` — useless alt text
- `![A detailed diagram showing the four layers of the Kwaxala stack including the Living Forest Fund at the top, Catalytic Commitment Facility below that, Living Forest Standard in the middle, and Tenured Forest Land at the bottom with arrows indicating capital flows](./slides/slide-09.jpg)` — too long; that belongs in the semantic description (P4)

Alt text is a short label. Semantic description (P4) is where the full explanation goes.

## Reference paths

**Always relative, never absolute.** Relative paths make the markdown portable across environments and commons locations.

```markdown
![Slide 9](./kwaxala-overview-2026-slides/slide-09.jpg)   ✓
![Slide 9](/Users/someone/some-project/slides/slide-09.jpg)   ✗
```

The path is relative to the markdown file's location. Don't use `../` unless absolutely necessary.

## Size budgets

Target sizes (per file):

- **Slide render**: ≤500KB. If larger, compress harder or reduce dpi.
- **Figure**: ≤300KB typically. Academic charts can be larger if they preserve meaningful precision.
- **Photo**: ≤400KB. Use JPEG q80 if tight.

**If an image is >500KB, flag it.** Either compress, downsample, or question whether it needs to be embedded at all (sometimes a link to the source is fine).

## When to extract assets vs embed inline

- **Extract to separate files** (the default): when the image is substantial (>20KB) and referenced from markdown
- **Embed as base64**: almost never — it bloats markdown and hurts portability. Only acceptable for very small icons or when the deliverable must be a single file

## Failure modes

- **Assets folder exists but isn't referenced from markdown.** Orphan files. Verify catches this.
- **Markdown references assets that don't exist.** Broken links. Verify catches this.
- **Absolute paths.** Breaks portability. Verify catches this.
- **Missing alt text.** Accessibility and AI-readability failure. Verify catches this.
- **Images larger than the source file.** Over-upscaled. Reduce DPI.
- **Decorative images extracted and referenced.** Skip decorative graphics — they add noise to the output without adding value.

## Deviation guidance

- Skip image extraction entirely for pure-text documents (simple-onepager often has no images worth extracting)
- Reduce DPI below defaults when source quality is already low
- Consolidate multiple tiny icons into a single "assets overview" note rather than extracting each one
- For images with meaningful text content (infographics, annotated diagrams), prefer PNG even if photos would be smaller, so text stays sharp
