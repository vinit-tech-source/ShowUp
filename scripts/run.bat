@echo off
setlocal enabledelayedexpansion

echo =======================================================
echo          ShowUp Desktop Application Launcher
echo =======================================================

:: 1. Check Python version
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in PATH.
    echo Please install Python 3.11 or newer from https://www.python.org/
    exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if %errorlevel% neq 0 (
    echo [ERROR] Python 3.11+ is required.
    python --version
    exit /b 1
)

:: 2. Set strict offline and privacy environment variables
set HF_HUB_DISABLE_TELEMETRY=1
set DO_NOT_TRACK=1
set TRANSFORMERS_OFFLINE=1

:: 3. Check Ollama availability
echo [*] Checking local Ollama service...
python -c "import urllib.request; urllib.request.urlopen('http://localhost:11434/api/tags', timeout=2)" >nul 2>nul
if %errorlevel% neq 0 (
    echo [NOTE] Ollama service is not currently running at http://localhost:11434.
    echo        ShowUp will use curated multilingual templates for message drafting.
    echo        To enable local LLM drafting, start Ollama: 'ollama serve'
) else (
    echo [+] Ollama service detected.
)

:: 4. Launch Streamlit UI
echo [*] Starting ShowUp desktop web app...
echo Open your browser at http://localhost:8501
streamlit run src\showup\ui\app.py --server.headless=true --server.address=localhost --server.port=8501

endlocal
