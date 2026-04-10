# Environments and Dependencies Matrix

Complete reference for platform-specific requirements, dependency installation, and environment variable setup across pathways.

## Dependency Matrix by Pathway

### Pathway 1 (YouTube Fast)

| Dependency | Requirement | Platform | Installation |
|------------|-------------|----------|--------------|
| yt-dlp | Download YouTube subtitles + audio | All | `pip install yt-dlp` |
| ffmpeg | Audio processing (fallback audio download) | All | macOS: `brew install ffmpeg`, Linux: `apt-get install ffmpeg`, Windows: `choco install ffmpeg` |
| OPENAI_API_KEY | Whisper API fallback (optional) | All | Environment variable; get key from https://platform.openai.com/api-keys |

**Total install time:** < 5 minutes
**Disk required:** ~500MB (yt-dlp cache + models)
**Runtime:** 30–120 seconds per video

---

### Pathway 2 (WhisperX Local)

| Dependency | Requirement | Platform | Installation | Notes |
|------------|-------------|----------|--------------|-------|
| yt-dlp | Audio download from YouTube URLs | All | `pip install yt-dlp` | If using YouTube source |
| ffmpeg | Audio format conversion and preprocessing | All | See P1 | Required for all sources |
| whisperx | Main transcription pipeline | All | `pip install git+https://github.com/m-bain/whisperx.git` | Requires git |
| faster-whisper | Underlying Whisper runner (auto-installed) | All | Bundled with whisperx | Verify: `pip list \| grep faster-whisper` |
| pyannote.audio | Speaker diarization and segmentation | All | `pip install pyannote.audio` | Requires HF_TOKEN (see below) |
| torch | PyTorch ML framework (CPU or GPU) | All | GPU: `pip install torch --index-url https://download.pytorch.org/whl/cu118` (CUDA 11.8) or `pip install torch` (CPU), macOS: `pip install torch` (includes MPS support), AMD: `pip install torch --index-url https://download.pytorch.org/whl/rocm5.7` | Installation varies by GPU |
| numpy | Numerical computing | All | `pip install numpy` | Auto-installed with whisperx |
| scipy | Scientific computing | All | `pip install scipy` | Auto-installed with whisperx |

**Total install time:** 10–30 minutes (includes model downloads)
**Disk required:** ~3GB (models: faster-whisper base ~1.5GB, pyannote ~400MB, cache ~500MB–1GB)
**Runtime:** 2–60+ minutes depending on audio length and GPU

---

### Pathway 3 (API Service)

| Dependency | Requirement | Platform | Installation |
|------------|-------------|----------|--------------|
| API client SDK | Service-specific (AssemblyAI, Deepgram, etc.) | All | `pip install assemblyai` or `pip install deepgram-sdk`, etc. |
| requests | HTTP client for polling | All | `pip install requests` (usually pre-installed) |
| API_KEY | Service authentication | All | Environment variable; vendor-specific |

**Total install time:** 2–5 minutes
**Disk required:** Minimal (~100MB)
**Runtime:** 30 seconds to 10 minutes (async, depends on service queue)

---

## Platform-Specific Notes

### macOS (Intel + Apple Silicon)

**Intel:**
- All pathways work as documented
- P2 GPU support: Metal Performance Shaders (MPS) available; enable with `torch.backends.mps.is_available()`
- CRITICAL: WhisperX's ctranslate2 **does NOT support MPS**. Force CPU for transcription/alignment via `CUDA_VISIBLE_DEVICES=""` and `TORCH_DEVICE=cpu`
- Pyannote CAN use MPS; set HF device explicitly

**Apple Silicon (M1, M2, M3, etc.):**
- Same as Intel, plus: MPS is the native GPU framework
- CRITICAL: **Must disable MPS for WhisperX** (ctranslate2 incompatibility); CPU inference only for alignment
- Pyannote uses MPS efficiently; ~4x speedup over CPU
- Performance: Transcription ~4x slower than NVIDIA GPU; diarization ~2x slower than GPU

**Mixed scenario (P2 on Apple Silicon):**
```bash
# Force WhisperX (faster-whisper, ctranslate2) to CPU
export CUDA_VISIBLE_DEVICES=""
export TORCH_DEVICE=cpu
export TORCH_DTYPE=float32

# Let pyannote use MPS for diarization
export HF_DEVICE=mps

# Run whisperx
python scripts/whisperx_local.py --input audio.mp3 --device cpu
```

### Linux (x86_64 + CUDA)

**Recommended:**
- NVIDIA GPU with CUDA 11.8 or 12.x (verify: `nvidia-smi`)
- cuDNN >= 8.0 (verify: check CUDA toolkit)
- ~8GB VRAM minimum for base model, 16GB+ for large model

**Installation:**
```bash
# Install CUDA 11.8 toolkit (example for Ubuntu 22.04)
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-ubuntu2204.pin
sudo mv cuda-ubuntu2204.pin /etc/apt/preferences.d/cuda-repository-pin-600
wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda-repo-ubuntu2204-11-8-local_11.8.0-520.61.05-1_amd64.deb
sudo dpkg -i cuda-repo-ubuntu2204-11-8-local_11.8.0-520.61.05-1_amd64.deb
sudo apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub
sudo apt-get update
sudo apt-get -y install cuda

# Install PyTorch with CUDA support
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

**CPU only (no GPU):**
- Install torch CPU version: `pip install torch` (defaults to CPU)
- Runtime expectation: 5–10x slower than GPU
- Viable for short clips (< 30 min) but not recommended for long-form

### Linux (AMD ROCm)

**Supported GPUs:** AMD Radeon RX 6000 series and newer

**Installation:**
```bash
# Install ROCm 5.7 (example; check AMD docs for latest)
wget -q -O - https://repo.radeon.com/rocm/rocm.gpg.key | sudo apt-key add -
echo 'deb [arch=amd64] https://repo.radeon.com/rocm/apt/debian jammy main' | sudo tee /etc/apt/sources.list.d/rocm.list
sudo apt-get update
sudo apt-get install rocm-hip-sdk

# Install PyTorch with ROCm support
pip install torch --index-url https://download.pytorch.org/whl/rocm5.7

# Verify
python -c "import torch; print(torch.cuda.is_available())"
```

### Windows

**Status:** Experimental; not thoroughly tested in production

**Prerequisites:**
- NVIDIA CUDA 11.8+ or CPU fallback
- Windows 10/11 (64-bit)
- Visual Studio Build Tools (for some dependencies)

**Installation:**
```bash
# Install PyTorch for Windows (CUDA)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install remaining dependencies
pip install whisperx pyannote.audio yt-dlp

# ffmpeg: Download from https://ffmpeg.org/download.html or
# choco install ffmpeg (if Chocolatey installed)
```

**Known issues:**
- Some users report Unicode/encoding issues with filenames; use ASCII-only output paths
- ffmpeg path not auto-detected; may need to add to PATH manually

---

## Environment Variables

### Required

**OPENAI_API_KEY** (P1 Whisper fallback, P2 optional backup)
```bash
export OPENAI_API_KEY="sk-..."
```
- Get from: https://platform.openai.com/api-keys
- Cost: ~$0.006/min (Whisper API)
- Keep secret; never commit to git

**HF_TOKEN** (P2 only; pyannote.audio)
```bash
export HF_TOKEN="hf_..."
```
- Get from: https://huggingface.co/settings/tokens
- Create token with read access
- Accept license for:
  - https://huggingface.co/pyannote/speaker-diarization-3.1
  - https://huggingface.co/pyannote/segmentation-3.0
- Test: `huggingface-cli login` or `python -c "import huggingface_hub; huggingface_hub.whoami()"`

### Optional (P2 Advanced)

**TORCH_DEVICE** — Override device detection
```bash
export TORCH_DEVICE=cpu  # Force CPU
export TORCH_DEVICE=cuda  # Force CUDA
export TORCH_DEVICE=mps  # Force MPS (macOS)
```

**TORCH_DTYPE** — Override precision
```bash
export TORCH_DTYPE=float32  # Full precision (safer, slower)
export TORCH_DTYPE=float16  # Half precision (faster, less accurate, may cause OOM relief)
```

**MDPOWERS_VOCAB** — Global vocabulary file
```bash
export MDPOWERS_VOCAB="/home/user/.config/mdpowers/vocabularies/master.json"
```

**HF_DEVICE** — Explicit device for Hugging Face models (pyannote)
```bash
export HF_DEVICE=mps  # macOS Metal
export HF_DEVICE=cuda  # NVIDIA GPU
export HF_DEVICE=cpu  # Fallback
```

---

## Model Cache Locations

Models are downloaded and cached automatically. Know where they live for troubleshooting.

### faster-whisper (Whisper models)

**Locations:**
- Default: `~/.cache/whisperx/` or `~/.cache/huggingface/hub/`
- Override: `WHISPERX_CACHE=/custom/path`

**Size by model:**
- tiny: ~70MB
- base: ~140MB
- small: ~460MB
- medium: ~1.5GB
- large: ~2.9GB

**Clean cache (if corrupted):**
```bash
rm -rf ~/.cache/whisperx/
rm -rf ~/.cache/huggingface/hub/models--openai--whisper-*
```

### pyannote.audio (diarization models)

**Locations:**
- Default: `~/.cache/huggingface/hub/`
- Models: `models--pyannote--speaker-diarization-3.1`, `models--pyannote--segmentation-3.0`

**Size:**
- speaker-diarization-3.1: ~400MB
- segmentation-3.0: ~50MB

**Clean cache:**
```bash
rm -rf ~/.cache/huggingface/hub/models--pyannote--*
```

### YouTube-dl (yt-dlp cache)

**Locations:**
- Default: `~/.cache/yt-dlp/` (Linux/macOS) or `%APPDATA%\yt-dlp\` (Windows)
- Override: `YT_DLP_CACHE=/custom/path`

**Size:** Depends on downloaded media; typically 1–5GB per month of use

---

## Installation Tiers

### Tier 1: Minimal (P1 only)

```bash
pip install yt-dlp
brew install ffmpeg  # macOS
apt-get install ffmpeg  # Linux
```

**Time:** 5 min
**Disk:** 500MB
**Use case:** Fast YouTube transcription only

### Tier 2: Standard (P1 + P2 basic)

```bash
pip install yt-dlp torch whisperx faster-whisper
brew install ffmpeg  # macOS
apt-get install ffmpeg  # Linux
export OPENAI_API_KEY="sk-..."
```

**Time:** 15–25 min (includes Whisper model download)
**Disk:** 2–3GB
**Use case:** Local transcription with basic diarization
**GPU:** Optional but recommended

### Tier 3: Full (P1 + P2 complete)

```bash
pip install yt-dlp torch whisperx faster-whisper pyannote.audio numpy scipy
brew install ffmpeg  # macOS
apt-get install ffmpeg  # Linux
export OPENAI_API_KEY="sk-..."
export HF_TOKEN="hf_..."
huggingface-cli login
```

**Time:** 20–30 min (includes all model downloads)
**Disk:** 3–4GB
**Use case:** Production-grade local transcription with full speaker diarization
**GPU:** Strongly recommended

---

## Dependency Check Script

Run before any pathway to validate environment:

```python
# scripts/probe_environment.py
import subprocess
import os
import sys

checks = {
    "Python": ("python --version", False),
    "yt-dlp": ("python -m pip show yt-dlp", True),
    "ffmpeg": ("ffmpeg -version | head -1", True),
    "torch": ("python -c 'import torch; print(torch.__version__)'", True),
    "cuda_available": ("python -c 'import torch; print(torch.cuda.is_available())'", False),
    "HF_TOKEN": ("echo $HF_TOKEN | cut -c1-4", False),
    "OPENAI_API_KEY": ("echo $OPENAI_API_KEY | cut -c1-4", False),
    "whisperx": ("python -c 'import whisperx; print(whisperx.__version__)'", False),
    "faster_whisper": ("python -c 'import faster_whisper; print(\"OK\")'", False),
    "pyannote": ("python -c 'import pyannote.audio; print(\"OK\")'", False),
}

for name, (cmd, required) in checks.items():
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        status = "✓" if result.returncode == 0 else "✗"
        output = result.stdout.strip() or result.stderr.strip()
        print(f"{status} {name:20s} {output[:60]}")
    except Exception as e:
        status = "✗" if required else "?"
        print(f"{status} {name:20s} Error: {str(e)[:50]}")
```

Run: `python scripts/probe_environment.py`
