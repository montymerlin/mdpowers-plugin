# API Service Transcription Pathway

## Status

**Not wired in v0.1.** This pathway is documented as a placeholder and design guide for future implementation. Code will raise `NotYetImplementedError` if invoked.

## When This Pathway Will Be Used

P3-api-service will be the preferred choice when:

- **Cloud processing desired** — no local compute, no GPU needed
- **Consistency across teams** — centralized vendor, same settings for all transcriptions
- **Budget-constrained audio** — pay per minute; avoid fixed infrastructure cost
- **Diarization included out-of-box** — vendor handles speaker identification
- **Compliance/audit trail** — vendor provides detailed logs and versioning
- **Speed at scale** — parallel processing for multiple files

Not recommended for:
- Proprietary or sensitive audio (privacy concerns with cloud upload)
- Offline/air-gapped environments
- Highly specialized vocabulary (limited customization in most services)
- Real-time transcription (most services are async)

## Candidate Services

### AssemblyAI

- **Per-minute cost:** ~$0.37/hour ($0.0062/min) recorded audio
- **Diarization:** Native speaker_labels endpoint
- **Alignment:** Yes, word-level timestamps included
- **Vocabulary:** Boost feature for custom terms (limited, 100 terms)
- **Latency:** 5–30 sec for 5 min audio (async, may queue)
- **Capacity:** High, reliable uptime
- **API design:** REST + Polling (no webhooks v0.1, may add later)
- **SDK:** Python: `pip install assemblyai`

### Deepgram Nova-2

- **Per-minute cost:** ~$0.43/hour ($0.0072/min)
- **Diarization:** Native, included in base API
- **Alignment:** Yes, word-level + confidence scores
- **Vocabulary:** Custom vocabulary training (powerful, but requires model training time)
- **Latency:** Fast, <10 sec for 5 min audio (streaming or REST)
- **Capacity:** Very high, enterprise-grade
- **API design:** gRPC streaming (also REST fallback)
- **SDK:** Python: `pip install deepgram-sdk`

### Rev.ai

- **Per-minute cost:** ~$1.25/hour ($0.021/min) — most expensive
- **Diarization:** Yes, but limited speaker accuracy (3–5 speakers max)
- **Alignment:** Word-level timestamps, moderate accuracy
- **Vocabulary:** PII redaction, technical vocabulary boost (limited domain coverage)
- **Latency:** Slow, 2–5 min for same-length audio (asynchronous only)
- **Capacity:** Medium, good for lower volume
- **API design:** REST async polling
- **SDK:** Python: Limited, mostly HTTP wrapper

### OpenAI Whisper API (No Native Diarization)

- **Per-minute cost:** ~$0.36/hour ($0.006/min) — lowest raw cost
- **Diarization:** None provided; would require post-processing with separate speaker ID service
- **Alignment:** Word-level timestamps in Whisper API v1.0+ (experimental)
- **Vocabulary:** Prompt-based boosting (same mechanism as local Whisper)
- **Latency:** <30 sec for most audio
- **Capacity:** High, reliable, used in production widely
- **Limitation:** No native diarization means two API calls needed (Whisper + speaker ID service)
- **SDK:** `pip install openai`

## v0.1 Behaviour

When invoked in v0.1, P3 will:

```python
raise NotYetImplementedError(
    "P3-api-service pathway is not yet implemented. "
    "Use P1 (YouTube fast) or P2 (WhisperX local) instead. "
    "P3 design is documented in references/pathways/P3-api-service.md"
)
```

User is directed to choose a different pathway.

## v0.2 Implementation Plan

### Phase 1: Service Selection & Integration

1. **Pick primary service** — Recommendation: **AssemblyAI** for balance of cost, diarization quality, and Python SDK maturity
2. **Add API key probe** — Add `ASSEMBLYAI_API_KEY` to environment check (similar to OPENAI_API_KEY)
3. **Implement service client wrapper** — Normalize API across AssemblyAI, Deepgram, Rev.ai (if time permits; start with one)
4. **Add service fallback logic** — If primary service fails, retry or suggest alternatives

### Phase 2: Upload & Polling

1. **File upload** — For local files: upload to service storage. For YouTube URLs: use P1 to fetch captions first, then upload if needed
2. **Async polling** — Submit request, store job ID, poll status every 5–10 sec until complete (timeout: 10 min soft, 30 min hard)
3. **Error handling** — Handle 429 (rate limit), 500 (server error), 401 (auth). Implement exponential backoff for retries
4. **Webhook support (optional)** — If service offers webhooks, register instead of polling for better UX

### Phase 3: Response Parsing & Enrichment

1. **Extract transcript** — Parse service response JSON, collect text and timestamps
2. **Speaker mapping** — If service returns speaker labels (SPEAKER_0, SPEAKER_1), map to names via metadata research + user override
3. **Word-level alignment** — If available, include word timestamps in markdown (same [HH:MM.ss] format as P2)
4. **Confidence scoring** — Capture confidence per word/segment for quality notes

### Phase 4: Cost Estimation & Reporting

1. **Pre-transcription estimate** — Calculate cost based on audio duration and service pricing
2. **Post-transcription actual** — Log actual billable minutes, service used, cost
3. **Cost summary in output** — Add to frontmatter: `api_cost: $0.12` and `service: assemblyai`
4. **Cumulative tracking** — Log total cost per session for user awareness

### Phase 5: Shared Enrichment Steps

1. **Vocabulary overlay** — After receiving transcript, apply same post-hoc correction as P2 (substring replacement, longest-match-first)
2. **Quirks review** — Scan for low-confidence words (< 0.85 from API), flag for manual review
3. **Speaker identification** — If service diarization incomplete, augment with metadata research + LLM guess (same flow as P2)
4. **Frontmatter assembly** — transcript_method: assemblyai (or deepgram, etc.), pathway: P3, quality: high (assuming service quality), cost added

## Runner Reference (Placeholder)

**Script:** `scripts/api_service.py` (not yet implemented)

**Planned usage:**
```bash
python scripts/api_service.py \
  --input "audio.mp3" \
  --output transcripts/my_transcript.md \
  --service assemblyai \
  --speakers "auto"
```

**Planned parameters:**
- `--input`: Local file or YouTube URL (required)
- `--output`: Output markdown path (optional)
- `--service`: assemblyai | deepgram | rev | openai (default: assemblyai)
- `--speakers`: Speaker names, "auto" for LLM guess, or file path to speaker list
- `--poll-interval`: Seconds between status checks (default: 5)
- `--max-wait`: Maximum seconds to wait for completion before timeout (default: 600)
- `--estimate-only`: Show cost estimate and exit without processing (optional boolean)

**Planned exit codes:**
- 0: Success
- 1: Invalid input
- 2: API key missing or invalid
- 3: Service error (500, timeout, etc.)
- 4: Cost estimate exceeds user budget (if --max-cost set)
- 5: Transcription timeout (exceeded --max-wait)
