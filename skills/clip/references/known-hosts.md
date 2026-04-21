# Known-Host Compatibility Catalogue

Observed behaviour per host, updated as new sources are attempted. Entries come from real clipping attempts — each row reflects a confirmed outcome, not a guess.

Use this before attempting a clip on a new URL. If the domain isn't listed, try Defuddle direct first, then follow the fallback cascade in `SKILL.md`.

---

## Defuddle direct — works

These hosts return full content via `defuddle parse --markdown` without special handling:

| Domain / pattern | Notes | Last confirmed |
|---|---|---|
| `ethichub.com/en/blog/*` | Standard blog posts | 2026-04-15 |
| `ethichub.com/en/docs/*` | Documentation pages | 2026-04-15 |
| `www.heifer.org/*` | Public-facing articles | 2026-04-15 |
| `teaandcoffee.net/*` | Trade publication | 2026-04-15 |
| `prnewswire.com/*` | Most press releases | 2026-04-15 |
| `thedefiant.io/*` | Crypto media | 2026-04-15 |
| `www.demia.net/blog/*` | Company blog | 2026-04-15 |
| Cell Press article pages | e.g. `cell.com`, `thelancet.com` | 2026-04-15 |
| `ceruleanventures.substack.com/p/*` | Non-paywalled posts only | 2026-04-15 |

---

## WebFetch direct — Defuddle blocked

Try WebFetch (`WebFetch` tool with the original URL) instead of Defuddle. Returns full verbatim article text.

| Domain / pattern | Notes | Last confirmed |
|---|---|---|
| `medium.com/<publication>/<slug>` | Standard Medium path only — custom subdomains do NOT work | 2026-04-15 |

---

## Wayback Machine required

Defuddle blocked and WebFetch blocked or thin. Use Wayback snapshot (see `SKILL.md` Step 2).

| Domain / pattern | Notes | Last confirmed |
|---|---|---|
| Custom Medium subdomains (e.g. `dacxi.medium.com`) | Blocks both Defuddle and WebFetch | 2026-04-15 |
| Cloudflare-aggressive sites (general) | Aggressive bot-blocking at CDN level | 2026-04-15 |

---

## Semantic Scholar only — full text blocked

Full text inaccessible via any automated method. Semantic Scholar API returns at minimum abstract + bibliographic metadata. Use abstract as graceful degradation (see academic cascade in `SKILL.md`).

| Domain / pattern | Notes | Last confirmed |
|---|---|---|
| `ssrn.com/*` | Cloudflare blocks all automated access including WebFetch | 2026-04-15 |
| Sage journals (`journals.sagepub.com/*`) | Most articles paywalled; no OA PDF via Unpaywall | 2026-04-15 |
| Taylor & Francis (`tandfonline.com/*`) | Many articles paywalled; check Unpaywall first | 2026-04-15 |

---

## No viable capture path

No automated method reaches useful content. Mark `capture_failed: true` in index entry.

| Source type | Why | Notes |
|---|---|---|
| Spotify-only podcasts | No transcript, no legitimate audio download path | Use `mdpowers:transcribe` if audio is separately accessible |
| SSRN with suppressed abstract | Cloudflare + no abstract in Semantic Scholar response | Rare but occurs |
| Paywalled Sage / T&F without author-preprint mirror | No OA version anywhere in cascade | Check Google Scholar "All versions" as last resort |

---

## How to contribute new entries

When you attempt a clip on a new domain and confirm the outcome, add a row to the appropriate section above. Format:

```
| `domain.com/path/*` | Brief note on why / what worked | YYYY-MM-DD |
```

Source: initial catalogue extracted from `bridging-worlds/research/ethichub/methodology-sources-index.legacy.md` (2026-04-15 EthicHub research pass).
