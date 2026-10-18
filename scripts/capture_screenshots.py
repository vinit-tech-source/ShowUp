"""Capture comprehensive Playwright screenshots of every ShowUp UI page.

Captures all 9 pages at 1440x900 and 1920x1080 across 3 required system states:
1. empty_db (Clean database with first-run onboarding states)
2. sample_data (Full synthetic clinic data loaded & scored)
3. sample_data_ollama_stopped (Sample data loaded with Ollama offline)
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from contextlib import suppress
from pathlib import Path

import httpx
from playwright.sync_api import Page, sync_playwright

from showup.config import get_settings
from showup.storage.database import get_session
from showup.storage.repositories import wipe_all
from showup.ui.components import load_sample_dataset

SCREENSHOTS_DIR = Path("docs/screenshots")
DEFAULT_BASE_URL = "http://localhost:8501"
OFFLINE_PORT = 8502
OFFLINE_BASE_URL = f"http://localhost:{OFFLINE_PORT}"

PAGES = [
    ("Home", ""),
    ("Import", "Import"),
    ("Dashboard", "Dashboard"),
    ("Risk_Scores", "Risk_Scores"),
    ("What-If", "What_If"),
    ("Messages", "Messages"),
    ("Feature_Audit", "Feature_Audit"),
    ("Privacy", "Privacy"),
    ("About", "About"),
]

VIEWPORTS = [
    (1440, 900),
    (1920, 1080),
]


def wait_for_streamlit_ready(page: Page) -> None:
    """Wait until Streamlit finishes running and rendering elements."""
    page.wait_for_selector("[data-testid=stApp]", timeout=25000)
    page.wait_for_timeout(1000)
    with suppress(Exception):
        page.wait_for_selector("[data-testid=stStatusWidget]", state="detached", timeout=15000)
    page.wait_for_timeout(600)


def capture_all_pages_in_state(state_name: str, base_url: str = DEFAULT_BASE_URL) -> list[Path]:
    """Capture screenshots for all pages across viewports in the given database state."""
    saved_files: list[Path] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for width, height in VIEWPORTS:
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()

            for page_name, url_slug in PAGES:
                target_url = f"{base_url}/{url_slug}" if url_slug else base_url
                try:
                    page.goto(target_url, timeout=30000)
                    wait_for_streamlit_ready(page)

                    filename = f"{state_name}_{page_name}_{width}x{height}.png"
                    file_path = SCREENSHOTS_DIR / filename
                    page.screenshot(path=str(file_path), full_page=False)
                    saved_files.append(file_path)
                    print(f"Captured: {file_path.name}")
                except Exception as err:
                    print(f"Error capturing {page_name} ({width}x{height}): {err}")

            context.close()

        browser.close()

    return saved_files


def wait_for_server(url: str, timeout: int = 20) -> bool:
    """Poll URL until server responds with 200 OK or timeout expires."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with suppress(Exception):
            r = httpx.get(url, timeout=2.0)
            if r.status_code == 200:
                return True
        time.sleep(0.5)
    return False


def main() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    settings = get_settings()

    print("=======================================================")
    print("      ShowUp — Capturing Playwright Screenshots        ")
    print("=======================================================")

    main_proc: subprocess.Popen[bytes] | None = None
    if not wait_for_server(DEFAULT_BASE_URL, timeout=1):
        print(f"Starting primary Streamlit server on {DEFAULT_BASE_URL}...")
        main_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "src/showup/ui/app.py",
                "--server.headless=true",
                "--server.address=localhost",
                "--server.port=8501",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not wait_for_server(DEFAULT_BASE_URL, timeout=30):
            if main_proc:
                main_proc.terminate()
            raise RuntimeError(f"Main Streamlit server on {DEFAULT_BASE_URL} failed to start.")
        print("Primary Streamlit server ready.")

    try:
        # State 1: Empty database
        print("\n--- [1/3] State: empty_db ---")
        with get_session() as session:
            wipe_all(data_dir=settings.data_dir, session=session)
        time.sleep(1)
        empty_shots = capture_all_pages_in_state("empty_db", base_url=DEFAULT_BASE_URL)

        # State 2: Sample data loaded & scored
        print("\n--- [2/3] State: sample_data ---")
        count = load_sample_dataset()
        print(f"Loaded {count} sample bookings into local database.")
        time.sleep(1)
        sample_shots = capture_all_pages_in_state("sample_data", base_url=DEFAULT_BASE_URL)

        # State 3: Sample data loaded with Ollama stopped/offline
        print("\n--- [3/3] State: sample_data_ollama_stopped ---")
        offline_env = os.environ.copy()
        offline_env["SHOWUP_OLLAMA_URL"] = "http://localhost:19999"

        offline_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "src/showup/ui/app.py",
                "--server.headless=true",
                "--server.address=localhost",
                f"--server.port={OFFLINE_PORT}",
            ],
            env=offline_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        try:
            print(f"Waiting for offline Streamlit server on {OFFLINE_BASE_URL}...")
            if not wait_for_server(OFFLINE_BASE_URL, timeout=25):
                raise RuntimeError(f"Server at {OFFLINE_BASE_URL} did not start in time.")
            print("Offline server ready. Capturing screenshots...")
            offline_shots = capture_all_pages_in_state(
                "sample_data_ollama_stopped", base_url=OFFLINE_BASE_URL
            )
        finally:
            offline_proc.terminate()
            with suppress(Exception):
                offline_proc.wait(timeout=5)

        total = len(empty_shots) + len(sample_shots) + len(offline_shots)
        print("\n=======================================================")
        print(f"Successfully captured {total} screenshots in {SCREENSHOTS_DIR.resolve()}")
        print("=======================================================")

    finally:
        if main_proc:
            print("Shutting down temporary primary Streamlit server...")
            main_proc.terminate()
            with suppress(Exception):
                main_proc.wait(timeout=5)


if __name__ == "__main__":
    main()
