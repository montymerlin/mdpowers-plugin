# Sandbox Setup Guide

<!-- SYNC NOTE: This file mirrors scripts/setup_wizard.py. Changes here must be reflected there. -->

Structured setup for Claude Code Cowork sandbox environment. This guide defines what the skill should do (tool calls) and what to ask the user (via AskUserQuestion), replacing terminal `input()` prompts with skill-native UI.

## Overview

Same nine steps as `setup.md`, but adapted for skill execution in Cowork with:
- No terminal `input()` prompts
- All questions via AskUserQuestion tool
- All file operations via Write/Edit tools
- Real-time progress updates via status messages

**Estimated time:** 5–20 minutes (same as local, but perceived faster due to UI)

---

## Step 1: Welcome and Environment Detection

### What the skill does:

1. **Detect platform** — Read `/etc/os-release` (Linux) or equivalent to identify OS
2. **Check Python version** — `sys.version_info`
3. **Probe dependencies** — `subprocess` calls to check installed packages
4. **Detect GPU** — Try `torch.cuda.is_available()`, `torch.backends.mps.is_available()`
5. **Report environment** — Format detected info into status message

### What to ask (AskUserQuestion):

```
title: "Welcome to mdpowers transcribe setup!"
subtitle: "Let's configure your transcription environment."

Body (display current environment summary):
  Platform: macOS (Apple Silicon)
  Python: 3.11.7
  GPU: Metal Performance Shaders (MPS) available
  
  Current dependencies:
    ✓ yt-dlp (Installed)
    ✓ ffmpeg (Installed)
    ✗ whisperx (Not found)
    ✗ pyannote.audio (Not found)

  Choose pathways:

options: [
  {label: "P1 only (YouTube fast, minimal setup)", value: "P1"},
  {label: "P1 + P2 (YouTube + local full pipeline)", value: "P1P2"},
  {label: "P1 + P2 + P3 (all pathways, including API)", value: "P1P2P3"}
]

default: "P1P2"
```

### What to write:

- `.mdpowers/config.json` (create if missing)
  ```json
  {
    "setup_completed": false,
    "pathways_enabled": ["P1", "P2"],
    "platform": "macOS",
    "python_version": "3.11.7",
    "gpu_available": true,
    "setup_timestamp": "2025-04-10T14:32:15Z"
  }
  ```

### Error handling:

- Python < 3.8: Show message "Python 3.8+ required. Current: X.Y.Z. Please upgrade."
- ffmpeg missing: Show "ffmpeg not found. Install via: brew install ffmpeg (macOS) / apt-get install ffmpeg (Linux) / download from ffmpeg.org (Windows). Then run setup again."
- No errors in Step 1: Continue to Step 2

---

## Step 2: Master Vocabulary Setup

### What the skill does:

1. **Check if file exists** — `os.path.exists("~/.config/mdpowers/vocabularies/master.json")`
2. **If exists:** Read and display summary
3. **If doesn't exist:** Prepare default template

### What to ask (AskUserQuestion):

```
title: "Master Vocabulary Setup"
subtitle: "Global vocabulary shared across all projects."

Body:
  A master vocabulary file stores domain-specific terms and their canonical forms.
  
  This is stored at: ~/.config/mdpowers/vocabularies/master.json
  
  Example content:
  {
    "defi": "DeFi",
    "regen": "Regen Network",
    "nft": "NFT"
  }

options: [
  {label: "Create new empty master", value: "create_empty"},
  {label: "I have a file at a custom path", value: "provide_path"},
  {label: "Skip for now", value: "skip"}
]

default: "create_empty"
```

### Sub-prompt if user chooses "provide_path":

```
title: "Provide master vocabulary file path"
input_type: "text"
placeholder: "/path/to/master.json"
hint: "Absolute path to your vocabulary JSON file"
```

### What to write:

If user chose **create_empty**:
- Create directory: `~/.config/mdpowers/vocabularies/` (if missing)
- Write file: `~/.config/mdpowers/vocabularies/master.json`
  ```json
  {
    "_meta": {
      "scope": "global",
      "created": "2025-04-10T14:32:15Z",
      "description": "Master vocabulary shared across all projects"
    }
  }
  ```

If user chose **provide_path**:
- Read provided file, validate JSON
- If invalid: Show error "Invalid JSON in file. Fix and try again or choose 'Create new empty'."
- If valid: Note path in `.mdpowers/config.json`

If user chose **skip**:
- Set `master_vocab: null` in config; continue

---

## Step 3: Project Overlay Setup

### What the skill does:

1. **Check if `.mdpowers/vocabularies/` exists** in current directory
2. **List existing vocabulary files** if directory exists
3. **Prepare default overlay template**

### What to ask (AskUserQuestion):

```
title: "Project Vocabulary Overlays"
subtitle: "Domain-specific vocabularies for this project."

Body:
  Project vocabularies override the master vocabulary and are stored in:
  .mdpowers/vocabularies/
  
  Current state: [directory exists/does not exist]
  
  You can have multiple overlays (e.g., vocabularies/regen.json, vocabularies/finance.json)
  and switch between them with the --vocab-overlay flag.

options: [
  {label: "Set up project vocabularies", value: "setup"},
  {label: "Use global master only", value: "skip"},
  {label: "Do this later", value: "defer"}
]

default: "setup"
```

### Sub-prompt if user chooses "setup":

```
title: "Project vocabulary domain"
input_type: "text"
placeholder: "e.g., regen, finance, podcast"
hint: "Short domain name for this project (optional)"
```

### Sub-prompt for vocabulary file:

```
title: "Add vocabulary file to project"
subtitle: "Provide a path or skip to create empty."

Body:
  If you have an existing vocabulary file, provide its path.
  Otherwise, I'll create an empty overlay.

input_type: "text"
placeholder: "/path/to/vocabulary.json"
hint: "Absolute path or 'skip' to create empty"
```

### What to write:

If user chose **setup**:
- Create directory: `.mdpowers/vocabularies/` (if missing)
- If user provided domain: Create `.mdpowers/vocabularies/{domain}.json`
  ```json
  {
    "_meta": {
      "scope": "{domain}",
      "created": "2025-04-10T14:32:15Z",
      "description": "Project-specific vocabulary"
    }
  }
  ```
- If user provided file path: Copy file to `.mdpowers/vocabularies/` (validate JSON)
- If user skipped file: Create empty overlay (as above)

If user chose **skip** or **defer**:
- Continue without creating directory

---

## Step 4: Host Path Capture (Sandbox Only)

### What the skill does:

1. **Detect sandbox** — Check for Cowork environment (env var `COWORK_MODE=1` or equivalent)
2. **If sandbox:** Offer to mount trusted host paths
3. **If local:** Skip this step

### What to ask (if in sandbox):

```
title: "Host Path Mounting (Sandbox)"
subtitle: "Safe file access to your computer (sandbox only)."

Body:
  In Cowork sandbox, I can mount directories from your computer
  for secure file input/output.
  
  This is optional. I can also save files locally in this project.

options: [
  {label: "Mount directory for transcripts", value: "mount"},
  {label: "Save locally in this project", value: "local"},
  {label: "Do this later", value: "defer"}
]

default: "local"
```

### Sub-prompt if user chooses "mount":

```
title: "Which host directory?"
input_type: "text"
placeholder: "~/Downloads, ~/Documents/Transcripts"
hint: "Absolute path on your computer (or relative to home ~)"
```

### What to write (if in sandbox and user mounts):

- Request host directory via request_cowork_directory tool
- Store in `.mdpowers/config.json`:
  ```json
  {
    "sandbox_host_path": "/Users/monty/Transcripts"
  }
  ```

### What to write (if local or user defers):

- Set in config:
  ```json
  {
    "output_path": "transcripts/"
  }
  ```

---

## Step 5: .gitignore Update

### What the skill does:

1. **Check if `.git/` exists** in current directory
2. **If yes:** Check `.gitignore` for `/.mdpowers/cache/` entry
3. **If entry missing:** Offer to add it

### What to ask (if git repo detected):

```
title: ".gitignore Configuration"
subtitle: "Exclude local transcription cache from git."

Body:
  Local transcription caches can be large (500MB–2GB+).
  I recommend adding .mdpowers/cache/ to .gitignore
  so they don't get committed to the repo.

options: [
  {label: "Add to .gitignore", value: "add"},
  {label: "Manual, I'll do it myself", value: "manual"},
  {label: "No thanks, skip", value: "skip"}
]

default: "add"
```

### What to write (if user chose "add"):

- Edit `.gitignore` (create if missing)
  - Add line: `/.mdpowers/cache/`
  - Preserve existing entries

---

## Step 6: Environment Variable Check

### What the skill does:

1. **Check env vars** — `os.getenv("OPENAI_API_KEY")`, `os.getenv("HF_TOKEN")`
2. **Report status** — Which are set, which are missing
3. **Offer guidance** — Links and instructions for each

### What to ask:

```
title: "Environment Variables"
subtitle: "API keys for transcription services."

Body:
  OPENAI_API_KEY: [not set / set ✓]
    (Needed for P1 Whisper fallback, optional for P2)
    Get: https://platform.openai.com/api-keys
    Set: export OPENAI_API_KEY="sk-..."
  
  HF_TOKEN: [not set / set ✓]
    (Needed only for P2 diarization)
    Get: https://huggingface.co/settings/tokens
    Accept license: https://huggingface.co/pyannote/speaker-diarization-3.1
    Set: export HF_TOKEN="hf_..."

options: [
  {label: "I'll set these in terminal", value: "manual"},
  {label: "Not needed yet, skip", value: "skip"}
]

default: "skip"
```

### What to write:

- Note in config: `env_keys_set: true/false`
- No actual keys stored in files (security best practice)

---

## Step 7: Dependency Check and Installation Offer

### What the skill does:

1. **Run full probe** — Test each dependency (yt-dlp, ffmpeg, torch, whisperx, pyannote)
2. **Group by pathway** — Show what's missing for P1, P2, P3
3. **Calculate install tier** — Minimal, standard, or full

### What to ask:

```
title: "Dependency Check"
subtitle: "Required packages for transcription."

Body:
  For P1 (YouTube fast):
    ✓ yt-dlp (installed)
    ✓ ffmpeg (installed)
  
  For P2 (WhisperX local):
    ✓ torch (installed)
    ✗ whisperx (NOT INSTALLED)
    ✗ pyannote.audio (NOT INSTALLED)

options: [
  {label: "Install missing packages via pip", value: "auto_install"},
  {label: "Show me the commands to run manually", value: "manual"},
  {label: "Skip for now", value: "skip"}
]

default: "auto_install"
```

### What to do if user chose "auto_install":

- Display progress status: "Installing whisperx... (this may take 5–10 min)"
- Run `pip install git+https://github.com/m-bain/whisperx.git` (subprocess)
- Run `pip install pyannote.audio` (subprocess)
- Display: "✓ Packages installed"
- If error: Show error message and suggest manual install

### What to display if user chose "manual":

```
Run these commands in your terminal:

pip install git+https://github.com/m-bain/whisperx.git
pip install pyannote.audio

Then re-run setup to verify installation.
```

### What to write:

- Update config with installed package versions

---

## Step 8: Model Prefetch (Optional)

### What the skill does:

1. **Check model cache** — Look for Whisper base model, pyannote models in `~/.cache/huggingface/`
2. **Estimate size** — ~2–3GB for full P2 models
3. **Estimate download time** — Based on detected internet speed (or assume 5MB/s)

### What to ask:

```
title: "Model Download"
subtitle: "Cache transcription models locally (optional)."

Body:
  Models needed for P2:
    - Whisper base model (~1.5GB)
    - pyannote speaker diarization (~400MB)
    - pyannote segmentation (~50MB)
  
  Total: ~2–3GB
  
  Prefetch now (5–20 min) or download on first use?

options: [
  {label: "Prefetch now", value: "prefetch"},
  {label: "Download on-demand", value: "ondemand"},
  {label: "I'll manage manually", value: "skip"}
]

default: "ondemand"
```

### What to do if user chose "prefetch":

- Display progress status: "Downloading Whisper base model... (1.5GB, ~5–10 min)"
- Run model download via whisperx/pyannote APIs
- Display checksum verification: "✓ Verifying... ✓ Checksums OK"
- If error: Show error, suggest on-demand fallback

### What to write:

- Note in config: `models_prefetched: true/false`

---

## Step 9: Completion Report

### What the skill does:

1. **Summarize all choices** — Pathways, vocabularies, dependencies, GPU
2. **Show file locations** — Where configs and cache live
3. **Provide quick-start commands** — Copy-paste ready for each pathway
4. **Offer next steps** — Run first transcription, read docs, etc.

### What to display:

```
title: "Setup Complete!"
subtitle: "You're ready to transcribe."

Body:

✓ Configuration Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pathways enabled:
  [X] P1 (YouTube fast)
  [X] P2 (WhisperX local)
  [ ] P3 (API services)

Vocabularies:
  Master: ~/.config/mdpowers/vocabularies/master.json
  Project: .mdpowers/vocabularies/regen.json

Environment:
  Platform: macOS
  GPU: Metal Performance Shaders (MPS)
  OPENAI_API_KEY: Set ✓
  HF_TOKEN: Not set (optional)

Dependencies:
  yt-dlp: ✓
  ffmpeg: ✓
  torch: ✓
  whisperx: ✓
  pyannote.audio: ✓

Models:
  whisper-base: Cached (~1.5GB)
  pyannote-diarization: Not cached (will download on-demand)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next Steps:

1. Try P1 (YouTube):
   → Run: python skills/transcribe/run.py --url "https://youtube.com/watch?v=..." --pathway P1

2. Try P2 (Local):
   → Run: python skills/transcribe/run.py --input audio.mp3 --pathway P2

3. Read documentation:
   → Pathways: skills/transcribe/references/pathways/
   → Vocabularies: skills/transcribe/references/playbooks/vocabulary-handling.md
   → Speaker ID: skills/transcribe/references/playbooks/speaker-identification.md

4. Troubleshooting:
   → Run: python scripts/probe_environment.py
   → Check: skills/transcribe/references/anti-patterns.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Configuration saved to: .mdpowers/config.json

```

### What to write:

- Final `.mdpowers/config.json` with all setup choices
- Create `.mdpowers/setup_complete` marker file (optional, for skipping future setup prompts)

---

## Error Recovery

### Installation fails (pip, torch, whisperx):

**Display:**
```
title: "Installation Error"
body: "pip install failed. Error: {error_msg}"

options: [
  {label: "Try again", value: "retry"},
  {label: "Show manual instructions", value: "manual"},
  {label: "Continue anyway (setup incomplete)", value: "skip"}
]
```

### Network timeout (model download):

**Display:**
```
title: "Download Interrupted"
body: "Model download timed out. Retrying..."

→ Automatic retry with exponential backoff (max 3 retries)
→ If still failed: Fall back to on-demand mode
```

### Permission denied (writing to ~/.config/):

**Display:**
```
title: "Permission Error"
body: "Can't write to ~/.config/mdpowers/. Using project-local storage instead."

→ Store master vocabulary in .mdpowers/vocabularies/master.json (project-level)
```

---

## Resumption & Idempotency

- **Check for `.mdpowers/config.json`** on setup start
- If exists and setup_completed=true: Ask "Setup already done. Re-run? [Y/n]"
- If incomplete: Resume from last completed step
- All file writes are idempotent (safe to overwrite or re-run)

---

## Comparison: Local vs. Sandbox

| Step | Local (`setup.md`) | Sandbox (`setup-sandbox.md`) |
|------|-------------------|------------------------------|
| **Prompt method** | `input()` in terminal | AskUserQuestion tool |
| **File operations** | Direct OS calls | Write/Edit/Read tools |
| **GPU detection** | Full PyTorch probe | Lightweight heuristic |
| **Network access** | Unrestricted | Routed through skill |
| **Dependency install** | `pip` directly | Subprocess in skill context |
| **Model download** | Direct cache write | Via skill's file tools |
| **Host path mount** | N/A | Via request_cowork_directory |

Both workflows perform identical configuration; only the UI and I/O mechanisms differ.
