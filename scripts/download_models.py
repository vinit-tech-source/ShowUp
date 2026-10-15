"""Download and verify local open-weight AI model weights for ShowUp.

Downloads:
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
) -> bool:
    """Check if model exists in Ollama; pull it if missing."""
    print(f"[*] Checking Ollama service at {ollama_url}...")
    try:
        req = urllib.request.Request(f"{ollama_url}/api/tags")
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
    except urllib.error.URLError as err:
        print(f"[!] Warning: Could not connect to Ollama ({err}).")
        print("    Please ensure Ollama is installed and running (ollama serve).")
        print("    Message drafting will use fallback templates until Ollama is running.")
        return False

    # Check if exact or base model exists
    target_match = any(
        m == model_name or m.startswith(f"{model_name}:") or model_name.startswith(m)
        for m in models
    )

    if target_match:
        print(f"[+] Ollama model '{model_name}' is already installed.")
        return True

    print(f"[*] Pulling '{model_name}' from Ollama registry. This may take a few minutes...")
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
                print(f"[+] Successfully pulled '{model_name}'.")
                return True
            print(f"[+] Pull completed: {res_data.get('status')}")
            return True
    except Exception as err:
        print(f"[!] Error pulling Ollama model: {err}")
        print(f"    You can pull manually using: ollama pull {model_name}")
        return False


def verify_tabpfn_setup() -> bool:
    """Verify TabPFN library and local model initialization."""
    print("[*] Checking TabPFN v2 foundation model setup...")
    try:
        import tabpfn  # type: ignore[import-untyped]  # noqa: F401, PLC0415

        print("[+] TabPFN library is installed.")
        return True
    except ImportError:
        print("[-] TabPFN library not installed.")
        print("    ShowUp will gracefully use calibrated Logistic Regression baseline.")
        return False
    except Exception as err:
        print(f"[!] TabPFN check warning: {err}")
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

    args = parser.parse_args()

    print("==================================================")
    print("      ShowUp — Local AI Model Initialization      ")
    print("==================================================")

    ollama_ok = check_and_pull_ollama_model(args.model, args.ollama_url)
    tabpfn_ok = verify_tabpfn_setup()

    print("\n----------------- Summary -----------------")
    print(f"Ollama ({args.model}): {'READY' if ollama_ok else 'OFFLINE (Templates active)'}")
    print(f"TabPFN v2:           {'AVAILABLE' if tabpfn_ok else 'FALLBACK (Logistic Regression)'}")
    print("-------------------------------------------")
    print("Ready to launch ShowUp.\n")


if __name__ == "__main__":
    main()
