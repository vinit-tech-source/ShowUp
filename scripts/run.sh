#!/usr/bin/env bash
set -euo pipefail

echo "======================================================="
echo "         ShowUp Desktop Application Launcher           "
echo "======================================================="

# 1. Check Python version (>= 3.11)
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 not found. Please install Python 3.11 or newer."
    exit 1
fi

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" || {
    echo "[ERROR] Python 3.11+ is required."
    python3 --version
    exit 1
}

# 2. Strict offline privacy environment variables
export HF_HUB_DISABLE_TELEMETRY=1
export DO_NOT_TRACK=1
export TRANSFORMERS_OFFLINE=1

# 3. Check Ollama availability
echo "[*] Checking local Ollama service..."
if python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2)" &> /dev/null; then
    echo "[+] Ollama service detected at http://localhost:11434."
else
    echo "[NOTE] Ollama service not detected at http://localhost:11434."
    echo "       ShowUp will use curated multilingual templates for message drafting."
    echo "       To enable local LLM drafting, start Ollama: 'ollama serve'"
fi

# 4. Launch Streamlit UI
echo "[*] Starting ShowUp desktop web app..."
echo "Open your browser at http://localhost:8501"
exec streamlit run src/showup/ui/app.py --server.headless=true --server.address=localhost --server.port=8501
