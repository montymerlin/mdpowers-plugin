# Podcast RSS Resolution Pathway

## What This Pathway Does

**P4-podcast-rss** is a pre-flight resolver, not a transcription engine. It turns a podcast platform URL (Spotify, Apple Podcasts, Buzzsprout episode page, etc.) into a locally downloaded audio file that P2 or P3 can transcribe. It also checks for existing transcripts before downloading — the fastest transcription is the one you don't have to run.

This pathway exists because podcast audio is almost always publicly accessible via RSS even when the platform UI is authenticated or the page is bot-blocked. The key insight: **podcast apps are just elegant RSS readers with a UI**. Nearly every show exposes its episodes as plain HTTP audio enclosures. The platform is a discovery layer, not an access gate.

## When to Use

Route to P4 when:
- User provides a Spotify podcast URL (episode or show)
- User provides an Apple Podcasts URL (`podcasts.apple.com/...`)
- User provides a Buzzsprout or Anchor.fm episode page URL
- User provides any podcast platform URL that isn't a direct audio file
- User provides a podcast show name + episode title with no URL
- Previous transcription attempt failed because audio was behind a platform login

**Do not** use P4 for:
- YouTube URLs → use P1 or P2 directly
- Direct audio file paths (mp3, m4a, wav) → use P2 directly
- Pure text sources → not a transcription problem

## The Four Steps

### Step 1: Discover the RSS Feed

**Goal:** Find the podcast's RSS feed from the platform URL or show name.

**Cascade (try in order, stop at first success):**

1. **Extract show/episode ID from URL.** Apple Podcasts IDs are in the path (`/id1234567890`). Spotify show IDs are in `open.spotify.com/show/XXXXXXXXX`. Buzzsprout show IDs are in the URL path.

2. **Apple Podcasts Lookup API** (for Apple/Spotify/generic show names):
   ```
   GET https://itunes.apple.com/lookup?id={APPLE_ID}&entity=podcast
   ```
   Returns `feedUrl` field with the RSS URL. Free, no auth, rate-limit-friendly.
   
   For show name search:
   ```
   GET https://itunes.apple.com/search?term={SHOW_NAME}&media=podcast&entity=podcast&limit=5
   ```

3. **Podcast Index API** (open, free, returns RSS for most shows):
   - Auth: HMAC-SHA1 with API key + secret (free registration at podcastindex.org)
   - Search by name: `GET https://api.podcastindex.org/api/1.0/search/byterm?q={SHOW_NAME}`
   - Returns `feed.url` for each result

4. **Known CDN/RSS patterns** — Some platforms expose RSS at a known path:
   - Buzzsprout: `https://feeds.buzzsprout.com/{SHOW_ID}.rss`
   - Anchor.fm: `https://anchor.fm/s/{SHOW_HASH}/podcast/rss`
   - Transistor: `https://feeds.transistor.fm/{SHOW_SLUG}`

**If RSS discovery fails:** Stop, report what was tried, and ask the user if they can paste the RSS feed URL directly (many podcast apps have "Copy RSS feed" in settings).

---

### Step 2: Check for Existing Transcripts

**Goal:** Before downloading and running WhisperX, check if a transcript already exists. This can save 20–60+ minutes.

**Check in order:**

1. **`podcast:transcript` tag in RSS item element.** Podcasting 2.0 namespace. If present, this is the canonical transcript:
   ```xml
   <podcast:transcript url="https://..." type="text/srt" />
   ```
   Supported types: `text/srt`, `text/vtt`, `application/json`, `text/html`. Download, parse, convert to mdpowers output format.

2. **Taddy.org API** — Free podcast transcript database. Covers a growing portion of popular English-language shows.
   ```
   GET https://api.taddy.org/podcast/{APPLE_ID}/episodes?includeTranscripts=true
   ```
   (Requires free API key.)

3. **Apple Podcasts** — Some shows have Apple's auto-generated transcripts. Available via the Apple Podcasts web player. Inconsistently exposed; worth checking for shows you know use it.

4. **Episode description / show notes** — If the RSS item's `<description>` or `<content:encoded>` field is unusually long (>2000 chars), it may contain an embedded transcript or full show notes. Worth inspecting before downloading audio.

**If an existing transcript is found:**
- Download it
- Convert to mdpowers output format (frontmatter + timestamped markdown)
- Note `transcript_method: existing_podcast_transcript` in frontmatter
- Flag `quality: unverified` if the source is auto-generated
- Proceed to Phase 4 (Review) — skip audio download entirely

---

### Step 3: Download Audio

**Goal:** Download the episode's audio file to a local path for P2/P3.

**Get the audio URL from the RSS enclosure:**

```xml
<enclosure url="https://cdn.example.com/episode123.mp3" type="audio/mpeg" length="45000000" />
```

The `url` attribute is the audio file. This URL is the canonical form — more stable than any platform-specific URL.

**Download handling:**

**Standard case** (most CDNs):
```bash
curl -L -o audio.mp3 "https://cdn.example.com/episode123.mp3"
```

**Signed CDN case** (Buzzsprout, Anchor/CloudFront, SoundOn):

Signed CDN URLs expire within seconds. A two-step approach (get URL → download separately) fails. Use a single command that follows all redirects before the signature window closes, with browser-mimicking headers:

```bash
curl -L \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  -H "Referer: https://www.buzzsprout.com/" \
  -H "Accept: audio/mpeg, audio/*, */*" \
  -o audio.mp3 \
  "https://www.buzzsprout.com/{SHOW_ID}/{EPISODE_ID}.mp3"
```

**Detecting signed URL CDNs:** If the enclosure URL is at a known signed CDN hostname (`d3ctxlq1ktw2nl.cloudfront.net`, `d3mrhpe9tif5dj.cloudfront.net`, `pdst.fm`, `chtbl.com`), or if a bare `curl` returns a small HTML file (< 50KB), apply the signed-URL pattern.

**Verify download:**
- Check file size is > 1MB (audio files are always multi-MB)
- Run `file audio.mp3` to confirm MPEG audio, not HTML
- Run `ffprobe audio.mp3` to get duration; compare against RSS `<itunes:duration>`

**Save to:** `.mdpowers/cache/{show_id}/{episode_id}/audio.mp3` (or `.m4a`)

---

### Step 4: Delegate to P2 or P3

Once audio is downloaded locally, treat it as a local audio file and route normally:

- **P2 (WhisperX)** — if whisperx is installed and diarization is wanted. Standard choice.
- **P3 (API Service)** — if no local whisperx or if cloud transcription is preferred.

**Pass through:**
- `--language` — from RSS `<language>` tag if present (e.g. `en`, `es`)
- `--vocab-overlay` — domain vocabulary if one exists for this show/topic
- `--speakers` — from RSS metadata: `<itunes:author>`, show notes, or user-provided names
- `--initial_prompt` — vocabulary terms for Whisper priming

## Metadata to Carry into Frontmatter

P4 collects richer metadata than other pathways because RSS is structured. These fields belong in the output frontmatter:

```yaml
source_type: podcast
source_url: https://open.spotify.com/episode/...  # original URL provided by user
rss_feed_url: https://feeds.buzzsprout.com/123456.rss
episode_title: "Episode 42 - Guest Name on Topic"
show_title: "Example Podcast"
episode_number: 42
published_date: 2025-01-15
duration_seconds: 1945
speakers:
  - Guest Name
  - Host Name
podcast_index_id: 7654321
apple_podcasts_id: 1234567890
```

## Failure Modes

| Failure | Handling |
|---------|----------|
| RSS feed returns 404 | Try iTunes Lookup API; try Podcast Index search; ask user for RSS URL directly |
| RSS feed found but no episodes | Show title is probably wrong; suggest the user verify the show name |
| All transcript checks negative | Proceed to audio download — this is the normal case |
| Buzzsprout curl returns HTML | Apply signed-CDN pattern (browser headers + `-L`) |
| Audio file verifies as < 1MB | CDN block or wrong URL; try getting enclosure URL directly from RSS feed rather than episode page |
| `ffprobe` fails on downloaded file | File is probably HTML (bot block); try adding browser headers; report clearly |
| Language not English and no vocab overlay | Warn user that vocabulary priming will be limited; proceed with auto-detect |

## What This Pathway Does NOT Do

- **Does not scrape authenticated content.** If a podcast is Spotify-exclusive (no public RSS), P4 cannot access it. Report this and ask if the user has a downloaded audio file.
- **Does not handle DRM.** Spotify's DRM-protected audio is not accessible. Same handling as above.
- **Does not run transcription.** P4 resolves audio and delegates. It is a pre-flight step, not a complete pipeline.

## Success Criteria

- RSS feed URL identified and validated
- Existing transcript checked (and used if found)
- Audio file downloaded, verified > 1MB, confirmed as audio by ffprobe
- Metadata extracted and ready for frontmatter
- Audio file path passed to P2 or P3 with metadata

## Discovery Context

This pathway was designed from a 2026-04 transcription session in which four podcast episodes had previously failed due to Spotify-only distribution and platform page 404s. Key learnings that informed this spec:

- Podcast Index API returns RSS feeds for most shows, even when the show page is Spotify-exclusive in the UI
- RSS enclosure URLs are nearly universal (~95% of podcasts) and bypass all platform authentication
- Buzzsprout CDN URLs require the signed-URL curl pattern — standard curl reliably fails
- Checking for `podcast:transcript` tags first saved significant compute time on one episode (found an existing SRT)
- Apple Podcasts Lookup API is unrestricted, fast, and returned correct RSS URLs for every show tested
