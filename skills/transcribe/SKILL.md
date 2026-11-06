---
name: transcribe
description: Transcribe audio or video (a meeting or screen recording, a talk, a podcast, a YouTube video) into speaker-labelled, timestamped markdown. Use when the user asks to "transcribe", "get a transcript", "transcribe this video/podcast/audio", mentions "diarization" or "speaker labels", or wants to know who said what in a recording.
---

# transcribe

**This skill states what a good transcript needs, not how to make one.** Speech recognition moves monthly. The tools named below are dated suggestions; check for better before using them (see *Keeping current*). If the workspace already has its own transcription tool or skill, prefer that and use this as the checklist.

**Privacy.** Recordings of meetings are usually other people's words. Prefer local models. Send audio, video or a transcript to a cloud service only with the user's explicit OK for that file or batch.

## What done looks like

| Stage | Objective · done when |
|---|---|
| **Source** | The best existing text is found before anything is transcribed. Use human-made captions, a podcast's own transcript (the RSS `podcast:transcript` tag), or the meeting platform's transcript if it is good enough. Otherwise extract the audio (mono 16 kHz is enough) |
| **Words** | Everything said is there, and nothing is silently dropped. A long silence in the text where the recording has speech is a failure to investigate. Check the word count against the length (about 120–160 words a minute in conversation) |
| **Second opinion** | A second model from a different family has transcribed the same audio. Every place the two disagree on a name, term or proper noun is decided from context or the audio. Neither model wins automatically; each catches what the other misses |
| **Turns** | A new block starts at each change of speaker, and voice clusters match real people. Diarization can merge or split people; flag it when in doubt |
| **Names** | Every speaker carries a real name, or `Speaker A/B…` with a note saying why. A name needs evidence: the on-screen label, a spoken introduction, the attendee list or episode notes, or the user. Never a guess |
| **Terms** | People, organisations and jargon are spelled right. Fix only distinctive casing automatically (ReFi, DAO). Treat a known-mistranscription list as suggestions to check in context, because many entries are ordinary phrases |
| **Output** | Markdown with YAML frontmatter: `source`, `method` (which models), `transcribed` (date), `reviewed: false`, `speakers`. Then `**Name** \`[mm:ss]\`` blocks, plus a short list of anything left for a human to check |

## Current suggestions (as of 2026-11; check for better first)

**Local, Apple Silicon.** These two were the strongest local pair in a November 2026 bake-off on a 26-minute, 5-speaker meeting, and they make different mistakes:
- **Parakeet TDT 0.6B v3**, via [parakeet-mlx](https://github.com/senstella/parakeet-mlx): the primary. It gives word timestamps (needed to merge with speaker turns), runs about 50× real time, and is consistent on acronyms.
- **Qwen3-ASR 1.7B**: the second opinion. Run it via the [Handy](https://github.com/cjpais/Handy) app's CLI (`handy --transcribe-file x.wav --json --model <id>`, text only, so transcribe each speaker stretch separately) or via [mlx-audio](https://github.com/Neywa-Labs/mlx-audio). It caught names and terms Parakeet missed, but was less consistent on acronyms.

**Speaker turns: [pyannote](https://github.com/pyannote/pyannote-audio) `speaker-diarization-community-1`.** It is open but gated on Hugging Face, so it needs a token. It runs on the Apple GPU (MPS) at roughly 15–25× real time, has no speaker cap, and separated 5 of 5 speakers in the test.
- Give each word the speaker whose turn holds its midpoint.
- Several newer models diarize in one pass (VibeVoice-ASR, Nemotron 3.5 Transcribe). In late 2026 they were capped at 8–10 speakers or were memory-hungry.

**Naming from a screen recording.** Meet and Zoom mark the active speaker's tile with a coloured border (2023 Meet: light blue; Zoom: green) and print the name under the tile.
- Sample frames at 1 fps, find the bordered tile and OCR its label. Apple's Vision framework does this with no install.
- Vote per voice cluster.
- In the test, this named every speaker correctly. No product or API did this.

**Other machines.** The same models run through NVIDIA NeMo or transformers on CUDA.

**Avoid (late 2026):**
- **WhisperX / faster-whisper on a Mac:** CPU-only, slower than real time, and in the bake-off it silently dropped about a fifth of the speech.
- **Granola:** cannot import recorded files.
- **OpenAI `gpt-4o-transcribe-diarize`:** shuts down on 26 Feb 2027 and caps files at 25 MB.
- **Blind find-and-replace from a mistranscription list.**

**Cloud, if the user approves.** AssemblyAI (names speakers from a supplied list) and Speechmatics (voiceprints, no training on data by default) were the most complete for long meetings. Check each provider's data-retention and training terms first.

## Keeping current

This is the part of the skill most likely to be wrong. Re-check the suggestions when:
- they are more than about six months old;
- before a large batch;
- when a run disappoints.

Where to look:
- the [Open ASR Leaderboard](https://huggingface.co/spaces/hf-audio/open_asr_leaderboard). The **AMI** column is the meeting-audio one; the long-form tab matters for hour-long files;
- the [Artificial Analysis speech-to-text](https://artificialanalysis.ai/speech-to-text) leaderboard, for cloud models;
- recent releases of parakeet-mlx, mlx-audio and pyannote, and the model list in Handy.

A new model earns a place only after a side-by-side test on a real recording. Measure:
- coverage, i.e. no dropped stretches;
- names and terms;
- speed.

When the pick changes, update this section and its date, and record why in the plugin's `CHANGELOG.md`.

## Changelog

- **0.5.0 (2026-11-06)** Rewritten as a lean, objective-led skill. The bundled WhisperX/pyannote pipeline (P2), the cloud-API stub (P3), the YouTube and podcast runners (P1, P4), the setup wizard and the vocabulary cascade are retired. See `DECISIONS.md` Decision 013.
