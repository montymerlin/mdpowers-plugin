#!/usr/bin/env bash
# install_nltk_data.sh — Download NLTK words corpus for vocabulary candidate discovery.
#
# This is a small download (~700KB). Idempotent — safe to re-run.
# Required for Path 2's vocabulary candidate discovery (the "rare/unusual words" category).
#
# Usage:
#   bash scripts/install_nltk_data.sh

set -e

echo "=== mdpowers transcribe: Downloading NLTK words corpus ==="
echo ""

python3 -c "
import nltk
print('Downloading NLTK words corpus...')
nltk.download('words', quiet=False)
print('Done.')
" 2>&1 || {
    echo "ERROR: NLTK download failed. Make sure nltk is installed:"
    echo "  pip install nltk"
    exit 1
}

echo ""
echo "=== NLTK data download complete ==="
