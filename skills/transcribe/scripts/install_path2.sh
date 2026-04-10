#!/usr/bin/env bash
# install_path2.sh — Install Path 2 (WhisperX local) heavy dependencies + prefetch models.
#
# This installs ~3GB of dependencies and model weights. Run once per machine.
# Tier 1 (core) deps should already be installed via: pip install -r requirements.txt
#
# Usage:
#   bash scripts/install_path2.sh
#
# NOTE: You must chmod +x this file on first local use if it doesn't have execute permission.

set -e

echo "=== mdpowers transcribe: Installing Path 2 (WhisperX local) ==="
echo ""

# Detect platform
OS="$(uname -s)"
ARCH="$(uname -m)"
echo "Platform: $OS / $ARCH"
echo ""

# Install Python packages
echo "--- Installing Python packages ---"
echo "This includes: whisperx, faster-whisper, pyannote.audio, torch, torchaudio, huggingface_hub, nltk"
echo ""

pip install --break-system-packages \
    whisperx \
    faster-whisper \
    pyannote.audio \
    torch \
    torchaudio \
    huggingface_hub \
    nltk \
    2>&1 || {
        echo ""
        echo "ERROR: pip install failed. Common fixes:"
        echo "  - Try: pip install --user --break-system-packages ..."
        echo "  - Or use a virtual environment: python -m venv .venv && source .venv/bin/activate"
        exit 1
    }

echo ""
echo "--- Python packages installed ---"
echo ""

# Prefetch WhisperX large-v2 model (~1.5GB)
echo "--- Prefetching WhisperX large-v2 model ---"
echo "This downloads the model weights (~1.5GB) so first transcription runs don't stall."
echo ""

python3 -c "
import whisperx
print('Loading WhisperX model (large-v2, CPU, int8)...')
model = whisperx.load_model('large-v2', device='cpu', compute_type='int8')
print('Model loaded and cached successfully.')
del model
" 2>&1 || {
    echo "WARNING: Model prefetch failed. The model will download on first use instead."
}

echo ""

# Prefetch pyannote speaker-diarization-3.1 (requires HF_TOKEN)
if [ -z "$HF_TOKEN" ]; then
    echo "--- Skipping pyannote model prefetch ---"
    echo "HF_TOKEN is not set. To prefetch the pyannote model:"
    echo "  1. Get a token at https://huggingface.co/settings/tokens"
    echo "  2. Accept the model license at https://huggingface.co/pyannote/speaker-diarization-3.1"
    echo "  3. Export HF_TOKEN=your_token and re-run this script"
else
    echo "--- Prefetching pyannote speaker-diarization-3.1 ---"
    python3 -c "
import os
from pyannote.audio import Pipeline
print('Loading pyannote speaker-diarization-3.1...')
pipeline = Pipeline.from_pretrained(
    'pyannote/speaker-diarization-3.1',
    use_auth_token=os.environ['HF_TOKEN']
)
print('Model loaded and cached successfully.')
del pipeline
" 2>&1 || {
        echo "WARNING: pyannote prefetch failed. Common causes:"
        echo "  - HF_TOKEN is invalid"
        echo "  - You haven't accepted the model license at:"
        echo "    https://huggingface.co/pyannote/speaker-diarization-3.1"
    }
fi

echo ""
echo "=== Path 2 installation complete ==="
echo ""
echo "Next steps:"
echo "  1. Run 'bash scripts/install_nltk_data.sh' to download the NLTK words corpus"
echo "  2. If HF_TOKEN was missing, set it and re-run this script to prefetch pyannote"
echo "  3. Run '/transcribe setup' to configure vocabulary and verify everything"
