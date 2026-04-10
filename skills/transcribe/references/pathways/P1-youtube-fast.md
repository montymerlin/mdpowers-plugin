# YouTube Fast Transcription Pathway

## When to Use This Pathway

**P1-youtube-fast** is the right choice when:

- Source is a **public YouTube video** with accessible subtitles or auto-captions
- Turnaround time is critical (<5 minutes preferred)
- Content is **single-speaker or clearly structured** (minimal speaker identification needed)
- You don't need phoneme-level alignment or speaker diarization
- You accept **degraded quality** if manual/auto-captions are unavailable and Whisper API fallback is triggered

This pathway is **not** recommended for:
- Videos requiring precise speaker boundaries and diarization
- Highly technical content where pronunciation variants matter
- Videos with overlapping speech or multiple indistinct speakers
- Archival or reproducible research where full local control is essential

## Preconditions

- **YouTube URL** is public and accessible (no login wall, not geo-blocked)
- **yt-dlp** installed (handles subtitles extraction, captions fallback)
- **Internet connection** for subtitle fetching and (optionally) Whisper API calls
- **OPENAI_API_KEY** environment variable set (Whisper API fallback only)
- No transcript already exists at output path (or user confirms overwrite)

## Steps

1. **Parse and validate the YouTube URL** — Confirm it's a valid YouTube URL (youtu.be or youtube.com pattern). Extract the video ID. Check if video is public by attempting lightweight HEAD request.

2. **Fetch subtitle metadata** — Use yt-dlp to list available subtitle tracks. Priority order: manual subtitles (user-generated) → auto-generated captions (YouTube automatic) → None available.

3. **Check for manual subtitles** — If manual subtitles exist, download them using yt-dlp in VTT format. This is the highest-quality, fastest path.

4. **Fall back to auto-captions if no manual subtitles** — Download YouTube's auto-generated captions (lang: user preference, default en). These are lower quality but usually fast.

5. **Convert VTT to timestamped markdown** — Parse VTT cue timing [HH:MM.ss] and content. Flatten overlapping cues. Remove duplicate text within 100ms. Build flat markdown section with timestamps embedded inline.

6. **Validate transcript length** — Confirm content is not empty. If <20 words total, raise TranscriptTooShort error.

7. **Check for speaker labels in captions** — Scan for speaker prefixes (e.g., "Host:" or speaker names followed by colon). If found, note in transcript_method field. Do NOT attempt diarization — just mark that labels were present.

8. **No subtitles available — invoke Whisper API fallback** — If both manual and auto-captions are unavailable: download audio (mp3, 128kbps max), upload to OpenAI Whisper API, poll for completion (~30–120 seconds depending on length). Parse JSON response, extract text segments with timestamps.

9. **Assemble frontmatter** — Populate YAML with: title (from YouTube metadata), source (youtube), channel (uploader name), published (from video date), duration (from video length), transcript_method (manual_subs | auto_captions | whisper_api), pathway (P1), quality (high | medium | degraded), quality_notes (brief reason if degraded).

10. **Write output file** — Save to user-specified path or default `{cwd}/transcripts/{YYYY-MM-DD}_{SafeTitle}_{video_id}.md`. Confirm before overwriting.

## What This Pathway Skips

- **Diarization** — Speaker identification and boundary detection. If multiple speakers exist in auto-captions, they appear as continuous text with no speaker block separation.
- **Alignment** — No phoneme-level or word-level alignment. Timestamps are cue-level only (typically 5–10 second blocks).
- **Quirks review** — No manual review phase for transcription errors, homophones, or context-specific corrections.
- **Vocabulary enrichment** — No vocabulary priming or post-hoc substring correction.
- **Speaker identification** — No metadata research, no LLM guess, no speaker mapping. User can optionally provide --speakers flag; otherwise speakers field is empty.
- **Audio download verification** — For Whisper fallback, we trust OpenAI's processing. No local audio inspection.

## Success Criteria

- ✓ Transcript file created at expected path
- ✓ Frontmatter is valid YAML, all required fields populated
- ✓ Markdown body contains at least one timestamped line
- ✓ All timestamps are in [HH:MM.ss] format and monotonically increasing
- ✓ No duplicate consecutive lines (same text within 100ms is merged)
- ✓ Output file is valid markdown (renders without syntax errors)

## Failure Modes & Handling

### Authentication Wall / Account-Only Videos

**Symptom:** yt-dlp reports 403 Forbidden or "Sign in to confirm you're not a bot."

**Handling:**
1. Warn user: "This video requires login or has account restrictions."
2. Do NOT attempt to retry or bypass.
3. Suggest alternative: "Download audio manually and use P2-whisperx-local, or provide a public mirror link."
4. Exit with AuthenticationError.

### Geo-Blocking

**Symptom:** yt-dlp reports 403 or video not found in user's region.

**Handling:**
1. Warn user: "This video is geo-blocked in your region."
2. Suggest: "Use a VPN or ask the video owner to lift geo-restrictions."
3. Exit with GeoBlockError.

### No Subtitles, No Auto-Captions, Whisper Fallback Unavailable

**Symptom:** yt-dlp finds no manual or auto captions. Either OPENAI_API_KEY is missing, or API call fails (rate limited, auth error, server error).

**Handling:**
1. Check OPENAI_API_KEY: If unset, prompt user to set it and retry.
2. If API call fails: Log error. Warn user with exact API error message. Suggest: "Retry in 60 seconds (rate limit) or check OpenAI account status (auth/quota)."
3. If user declines Whisper fallback: Prompt for alternative (download audio manually, provide subtitle file, use P2).
4. Exit gracefully; do NOT produce a half-transcript.

### Rate-Limited (Whisper API)

**Symptom:** OpenAI API returns 429 Too Many Requests.

**Handling:**
1. Log request and timestamp.
2. Extract retry_after header if present; else default to 60 seconds.
3. Offer to user: "This endpoint is rate-limited. Retry in {retry_after}s? (Y/n)"
4. If yes: sleep and retry (max 3 retries).
5. If no: Exit with RateLimitedError, log for future backoff.

## Runner Reference

**Script:** `scripts/yt_fast.py`

**Usage:**
```bash
python scripts/yt_fast.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --output transcripts/my_transcript.md \
  --quality-threshold high
```

**Key parameters:**
- `--url`: YouTube URL (required)
- `--output`: Output file path (optional; default: `{cwd}/transcripts/{auto_named}.md`)
- `--quality-threshold`: Minimum acceptable quality (high | medium | degraded; default: medium). If auto-captions or Whisper fallback selected, quality downgrades to medium/degraded.
- `--speakers`: Comma-separated speaker names (optional; populates speakers field)
- `--no-whisper-fallback`: Disable Whisper API fallback; fail if no captions (optional boolean)

**Exit codes:**
- 0: Success
- 1: Invalid URL
- 2: Video not found / access denied
- 3: Authentication wall / geo-block
- 4: No subtitles available (Whisper fallback disabled or failed)
- 5: Rate limited (retry advised)

**Typical runtime:** 30–120 seconds (depending on video length and caption availability).
