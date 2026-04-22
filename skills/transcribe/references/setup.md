# Local Mode Interactive Setup

Complete walkthrough for setting up mdpowers transcribe skill in local terminal environment. This guide is narrative (step-by-step) and interactive; the skill prompts the user for input at each stage.

## Overview

This setup process configures:
1. Master vocabulary (global default)
2. Project-specific vocabulary overlays
3. Transcription preferences and paths
4. Environment variables (API keys)
5. Dependency installation
6. Model prefetch (optional)

**Estimated time:** 10–30 minutes (depending on existing setup and model download)

---

## Step 1: Welcome and Environment Detection

**What it does:**
- Greets user
- Detects current platform (macOS, Linux, Windows)
- Checks if dependencies are already installed
- Reports environment status (GPU available? Python version? etc.)

**What it asks:**
```
Welcome to mdpowers transcribe setup!

I'll guide you through configuring the skill for your system.

Current environment:
  Platform: macOS (Apple Silicon)
  Python: 3.11.7
  GPU: Metal Performance Shaders (MPS) available
  yt-dlp: Installed ✓
  ffmpeg: Installed ✓
  torch: Not found
  whisperx: Not found
  pyannote.audio: Not found

Question: Which transcription pathways do you want to use?
  [1] P1 only (YouTube fast, minimal setup)
  [2] P1 + P2 (YouTube + local full pipeline)
  [3] P1 + P2 + P3 (all pathways, including API services)
  
Choose [default=2]:
```

**What files it writes:**
- `.mdpowers/config.json` (stores pathway selection for future runs)

**What can go wrong:**
- Python 3.8+: If < 3.8, suggest upgrade
- Missing ffmpeg: Offer installation command for platform
- No sudo access: Advise user to install manually or use venv

---

## Step 2: Master Vocabulary Setup

**What it does:**
- Checks if `~/.config/mdpowers/vocabularies/master.json` exists
- If not, offers to create one
- If exists, asks if user wants to review or replace

**What it asks:**
```
Step 2: Master Vocabulary (Global Default)

This is your global vocabulary file, shared across all projects.

Question: Do you have a master vocabulary file?
  [Y]es, I have one at a custom path
  [N]o, create a new empty one
  [S]kip, I'll add it later
  
Choose [default=N]:

If [Y]: "Where is your file?" → provide path
If [N]: "I'll create an empty master vocabulary at ~/.config/mdpowers/vocabularies/master.json"
If [S]: Continue (master will be empty for now)
```

**What files it writes:**
- `~/.config/mdpowers/vocabularies/master.json` (if created)
  ```json
  {
    "_meta": {
      "scope": "global",
      "created": "2025-04-10T14:32:15Z",
      "description": "Master vocabulary shared across all projects"
    }
  }
  ```

**What can go wrong:**
- Directory doesn't exist: Create `~/.config/mdpowers/vocabularies/` automatically
- Permission denied: Offer to use alternative location
- Invalid JSON provided: Validate and prompt for fix

---

## Step 3: Project Overlay Setup

**What it does:**
- Checks if current project has `.mdpowers/vocabularies/` directory
- If not, offers to create one
- Helps user populate with domain-specific vocabulary overlays

**What it asks:**
```
Step 3: Project Vocabulary Overlays

This directory stores vocabulary specific to your current project.

Question: Do you want to set up project-specific vocabularies?
  [Y]es, create the directory and add vocabularies
  [N]o, use global master only
  [S]kip, I'll do this later
  
Choose [default=Y]:

If [Y]:
  "What domain is this project? (e.g., 'finance', 'podcast', 'regen')"
  → User enters domain → Create .mdpowers/vocabularies-{domain}/ or .mdpowers/vocabularies/
  
  "Do you have a vocabulary file to add? (path or skip)"
  → If path provided: Copy to .mdpowers/vocabularies/{filename}
  → If skip: Create empty overlay
```

**What files it writes:**
- `.mdpowers/vocabularies/` (directory)
- `.mdpowers/vocabularies/{domain}.json` (if user provides one)
  ```json
  {
    "_meta": {
      "scope": "{domain}",
      "created": "2025-04-10T14:32:15Z",
      "description": "Project-specific vocabulary for {domain}"
    }
  }
  ```

**What can go wrong:**
- Overwriting existing overlay: Warn and ask for confirmation
- Invalid JSON in provided file: Validate and show error with fix suggestion

---

## Step 4: Host Path Capture (Sandbox Only)

**What it does:**
- Checks if user is in a sandboxed skill execution environment
- If yes, captures trusted host paths for safe file I/O
- If no (local mode), skips this step

**What it asks (Sandbox only):**
```
Step 4: Host Path Mounting (Sandbox)

If you're running this in a sandboxed host, I can mount
directories from your computer for safe file access.

Question: Do you want to mount a directory for transcripts?
  [Y]es, mount my Downloads folder (or specify custom path)
  [N]o, save transcripts locally in this project
  
Choose [default=N]:

If [Y]:
  "Which host directory? (e.g., ~/Downloads, ~/Documents/Transcripts)"
  → Skill mounts path; stores in .mdpowers/config.json for future sessions
```

**What it asks (Local mode):**
```
(Skipped - you're running locally. Output paths default to
 {cwd}/transcripts/ or your --output flag.)
```

**What files it writes:**
- `.mdpowers/config.json` (updated with host_path if mounted)

**What can go wrong:**
- Path doesn't exist on host: Ask for confirmation before mounting
- Permission denied: Suggest alternative path
- Sandbox not detected: Skip gracefully (local mode default)

---

## Step 5: .gitignore Update

**What it does:**
- Checks if project uses git
- If yes, ensures `.mdpowers/cache/` is in `.gitignore`
- Explains why cache shouldn't be committed

**What it asks:**
```
Step 5: Git Configuration

Question: Is this a git project?
  [Y]es
  [N]o
  
Choose [default=auto-detect]:

If [Y]:
  "I'll add .mdpowers/cache/ to .gitignore so local transcription
   caches don't get committed. This keeps the repo lean."
   
  Confirm? [Y/n]: (default=Y)
```

**What files it writes:**
- `.gitignore` (appended with `/.mdpowers/cache/` if not already present)

**What can go wrong:**
- .gitignore doesn't exist: Create it
- .gitignore has other entries: Append without removing existing
- Git not initialized: Skip and continue

---

## Step 6: Environment Variable Check

**What it does:**
- Checks if `OPENAI_API_KEY` and `HF_TOKEN` are set
- For each missing key, offers guidance on how to set it
- Does NOT prompt user to enter keys directly (security best practice)

**What it asks:**
```
Step 6: API Keys and Environment Variables

Checking for required credentials...

OPENAI_API_KEY: Not set (needed for P1 Whisper fallback, optional for P2)
HF_TOKEN: Not set (needed only for P2 diarization)

Question: Do you want to set these now?
  [Y]es, show me how
  [N]o, I'll set them later
  [S]kip, I don't need them yet
  
Choose [default=N]:

If [Y]:
  OPENAI_API_KEY:
    Get one at: https://platform.openai.com/api-keys
    Set via: export OPENAI_API_KEY="sk-..."
    Or add to ~/.bashrc or ~/.zshrc for permanent storage
  
  HF_TOKEN:
    Get one at: https://huggingface.co/settings/tokens
    Accept license: https://huggingface.co/pyannote/speaker-diarization-3.1
    Set via: export HF_TOKEN="hf_..."
    Or run: huggingface-cli login
  
  Test with: python -c "import os; print(os.getenv('OPENAI_API_KEY', 'not set'))"
```

**What files it writes:**
- None (keys are environment variables, not stored in files)

**What can go wrong:**
- User doesn't have accounts yet: Provide signup links
- Keys already set: Confirm and continue
- Invalid key format: Offer to test (don't validate against service)

---

## Step 7: Dependency Check and Installation Offer

**What it does:**
- Runs full dependency probe (yt-dlp, ffmpeg, torch, whisperx, pyannote, etc.)
- For each missing dependency needed for selected pathways, offers installation
- Groups by install tier (minimal, standard, full)

**What it asks:**
```
Step 7: Dependencies

Checking for required packages...

For P1 (YouTube fast):
  ✓ yt-dlp: Installed (2025.4.10)
  ✓ ffmpeg: Installed (6.1)
  
For P2 (WhisperX local):
  ✓ torch: Installed (2.1.2)
  ✗ whisperx: NOT INSTALLED
  ✗ faster-whisper: NOT INSTALLED
  ✗ pyannote.audio: NOT INSTALLED

Question: Install missing dependencies?
  [Y]es, install via pip
  [M]anual, show me the commands
  [N]o, skip for now
  
Choose [default=Y]:

If [Y]:
  "Installing P2 dependencies... (this may take 5–15 minutes)"
  → Run: pip install git+https://github.com/m-bain/whisperx.git
  → Run: pip install pyannote.audio
  → Show progress
  
If [M]:
  "Run these commands manually:
   pip install git+https://github.com/m-bain/whisperx.git
   pip install pyannote.audio
   Then re-run setup to verify."
```

**What files it writes:**
- None (pip install is in-place)

**What can go wrong:**
- Installation fails (network, permission): Show error and suggest offline docs
- Old pip version: Suggest upgrade (`pip install --upgrade pip`)
- Git not available (for git+https:// URLs): Suggest alternative install method

---

## Step 8: Model Prefetch (Optional)

**What it does:**
- Checks if Whisper and pyannote models are cached
- If not, offers to prefetch them (large download, may take 5–30 min depending on bandwidth)
- Allows user to skip and let models download on-demand

**What it asks:**
```
Step 8: Model Download (Optional)

Transcription models need to be downloaded once and cached.

Question: Prefetch models now or on-demand?
  [P]refetch (download now, ~3–4GB for P2 full)
  [O]n-demand (download on first use)
  [S]kip, I'll manage manually
  
Choose [default=O]:

If [P]:
  "This will download:
    - Whisper base model (~1.5GB)
    - pyannote speaker diarization (~400MB)
    - pyannote segmentation (~50MB)
   Total: ~2–3GB
   
   Proceed? [Y/n]:"
   
   → Show progress bars for each model
   → Verify checksums after download

If [O]:
  "Models will download automatically when you first run the skill.
   Expect 2–5 min added to first transcription."

If [S]:
  Continue without predownloading.
```

**What files it writes:**
- Model cache: `~/.cache/huggingface/hub/` (if [P] chosen)

**What can go wrong:**
- Bandwidth issue: Offer to split download or use alternative method
- Disk space error: Check available space and suggest cleanup
- Corrupted download: Delete cache and retry

---

## Step 9: Completion Report

**What it does:**
- Summarizes all setup choices
- Shows where files are stored
- Provides quick-start commands for each pathway
- Offers next steps (run first transcription, read docs, etc.)

**What it displays:**
```
✓ Setup Complete!

Configuration Summary:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Pathways enabled:
  [X] P1 (YouTube fast)
  [X] P2 (WhisperX local)
  [ ] P3 (API services)

Vocabularies:
  Master: ~/.config/mdpowers/vocabularies/master.json
  Project: .mdpowers/vocabularies/
  Active overlays: 1 (regen-core.json)

Environment:
  OPENAI_API_KEY: Set ✓
  HF_TOKEN: Not set (optional for P2)
  Platform: macOS Intel
  GPU: CUDA available

Dependencies:
  yt-dlp: ✓
  ffmpeg: ✓
  torch: ✓
  whisperx: ✓
  pyannote.audio: ✓

Models cached:
  whisper-base: ✓ (~1.5GB)
  pyannote-diarization: ✓ (~400MB)
  pyannote-segmentation: ✓ (~50MB)

Output path: {cwd}/transcripts/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next Steps:

1. Try P1 (YouTube):
   python skills/transcribe/run.py \
     --url "https://youtube.com/watch?v=..." \
     --pathway P1

2. Try P2 (Local):
   python skills/transcribe/run.py \
     --input audio.mp3 \
     --pathway P2

3. Read full docs:
   → skills/transcribe/references/
   → pathways/P1-youtube-fast.md
   → pathways/P2-whisperx-local.md

4. Set up vocabulary:
   → Docs: playbooks/vocabulary-handling.md
   → Current master: ~/.config/mdpowers/vocabularies/master.json

Questions or issues?
   → See references/ folder for troubleshooting
   → Run: python scripts/probe_environment.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**What files it writes:**
- `.mdpowers/config.json` (final summary saved for future runs)
  ```json
  {
    "setup_completed": true,
    "setup_timestamp": "2025-04-10T14:32:15Z",
    "pathways_enabled": ["P1", "P2"],
    "master_vocab": "~/.config/mdpowers/vocabularies/master.json",
    "project_vocab": ".mdpowers/vocabularies/",
    "output_path": "transcripts/",
    "platform": "macOS",
    "gpu_available": true,
    "dependencies": {
      "yt-dlp": "2025.4.10",
      "ffmpeg": "6.1",
      "torch": "2.1.2",
      "whisperx": "latest",
      "pyannote.audio": "3.0"
    }
  }
  ```

**What can go wrong:**
- Config file write fails: Warn but continue (setup succeeded, just can't save state)
- Broken links in next steps: Verify paths exist before showing

---

## Troubleshooting During Setup

### If Python version is < 3.8
- **Issue:** Some dependencies require Python 3.8+
- **Resolution:** Show download link for Python 3.11+ and suggest updating PATH

### If ffmpeg installation fails
- **Issue:** Network error, package manager not available
- **Resolution:** Provide manual download link; skip and continue with warning

### If pip install times out
- **Issue:** Network congestion or PyPI rate limit
- **Resolution:** Retry with exponential backoff; suggest offline alternative or split install

### If torch GPU detection fails
- **Issue:** CUDA drivers not installed or mismatched
- **Resolution:** Fall back to CPU; show installation link for drivers; continue

### If HF_TOKEN test fails
- **Issue:** Token invalid or license not accepted
- **Resolution:** Remind user to accept license at https://huggingface.co/pyannote/speaker-diarization-3.1; offer retry

### If model download is interrupted
- **Issue:** Network failure during large download
- **Resolution:** Delete partial cache; offer to resume or skip; continue

---

## Summary

This setup walkthrough ensures users start with:
- Functional dependencies for chosen pathways
- API keys configured (or at least documented)
- Vocabulary system ready (global + project)
- Output paths set up
- Models cached (or auto-download configured)

Users can always re-run setup to change settings or repair a broken environment.
