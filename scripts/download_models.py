"""Download and verify local open-weight AI model weights for ShowUp.

Downloads / verifies:
1. Gemma model via local Ollama instance (default: gemma3:4b).
2. Verifies TabPFN v2 local foundation model availability.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request

# Enforce zero telemetry during model setup
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["DO_NOT_TRACK"] = "1"


def check_and_pull_ollama_model(
    model_name: str,
    ollama_url: str = "http://localhost:11434",
    pull_if_missing: bool = False,
) -> bool:
    """Check if model exists in Ollama; pull it if missing and requested."""
    print(f"[*] Checking Ollama service at {ollama_url}...", flush=True)
    try:
        req = urllib.request.Request(f"{ollama_url}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
    except urllib.error.URLError as err:
        print(f"[!] Warning: Could not connect to Ollama ({err}).", flush=True)
        print("    Please ensure Ollama is installed and running (ollama serve).", flush=True)
        print(
            "    Message drafting will use fallback templates until Ollama is running.", flush=True
        )
        return False

    if models:
        print(f"[+] Connected to Ollama. Installed models: {models}", flush=True)
    else:
        print("[+] Connected to Ollama. (No models currently installed)", flush=True)

    # Check if exact or base model exists
    target_match = any(
        m == model_name or m.startswith(f"{model_name}:") or model_name.startswith(m)
        for m in models
    )

    if target_match:
        print(f"[+] Ollama model '{model_name}' is verified and ready.", flush=True)
        return True

    if not pull_if_missing:
        print(
            f"[-] Model '{model_name}' is not currently installed in Ollama.",
            flush=True,
        )
        print(
            f"    To download it now, run: ollama pull {model_name}",
            flush=True,
        )
        print(
            "    Or pass --pull to this script: python scripts/download_models.py --pull",
            flush=True,
        )
        if models:
            tip_msg = f"    Tip: You can use '{models[0]}' via SHOWUP_OLLAMA_MODEL={models[0]}"
            print(tip_msg, flush=True)
        return False

    print(
        f"[*] Pulling '{model_name}' from Ollama registry. Please wait...",
        flush=True,
    )
    pull_url = f"{ollama_url}/api/pull"
    payload = json.dumps({"name": model_name, "stream": False}).encode("utf-8")
    req = urllib.request.Request(
        pull_url,
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            if res_data.get("status") == "success":
                print(f"[+] Successfully pulled '{model_name}'.", flush=True)
                return True
            print(f"[+] Pull finished: {res_data.get('status')}", flush=True)
            return True
    except Exception as err:
        print(f"[!] Error pulling Ollama model: {err}", flush=True)
        print(f"    You can pull manually using: ollama pull {model_name}", flush=True)
        return False


def verify_tabpfn_setup() -> bool:
    """Verify TabPFN library and local model initialization."""
    print("[*] Checking TabPFN v2 foundation model setup...", flush=True)
    try:
        import tabpfn  # type: ignore[import-untyped]  # noqa: F401, PLC0415

        print("[+] TabPFN library is installed.", flush=True)
        return True
    except ImportError:
        print("[-] TabPFN library not installed.", flush=True)
        print(
            "    ShowUp will gracefully use calibrated Logistic Regression baseline.",
            flush=True,
        )
        return False
    except Exception as err:
        print(f"[!] TabPFN check warning: {err}", flush=True)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify and pre-load local models for ShowUp.")
    parser.add_argument(
        "--model",
        type=str,
        default="gemma3:4b",
        help="Ollama model tag to pull/verify (default: gemma3:4b).",
    )
    parser.add_argument(
        "--ollama-url",
        type=str,
        default="http://localhost:11434",
        help="Base URL for Ollama daemon (default: http://localhost:11434).",
    )
    parser.add_argument(
        "--pull",
        action="store_true",
        help="Automatically pull the model from Ollama registry if missing.",
    )

    args = parser.parse_args()

    print("==================================================", flush=True)
    print("      ShowUp -- Local AI Model Initialization     ", flush=True)
    print("==================================================", flush=True)

    ollama_ok = check_and_pull_ollama_model(args.model, args.ollama_url, pull_if_missing=args.pull)
    tabpfn_ok = verify_tabpfn_setup()

    print("\n----------------- Summary -----------------", flush=True)
    ollama_status = "READY" if ollama_ok else "OFFLINE / NOT PULLED (Templates active)"
    print(f"Ollama ({args.model}): {ollama_status}", flush=True)
    print(
        f"TabPFN v2:           {'AVAILABLE' if tabpfn_ok else 'FALLBACK (Logistic Regression)'}",
        flush=True,
    )
    print("-------------------------------------------", flush=True)
    print("Ready to launch ShowUp.\n", flush=True)


if __name__ == "__main__":
    main()
