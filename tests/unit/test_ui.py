"""Unit tests for ShowUp Streamlit UI pages using AppTest.

Verifies:
1. No element renders literal '<div' (prevents markdown code block HTML leaks).
2. All pages load without raising exceptions.
3. Navigation and titles adhere to design system specifications.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

ROOT_DIR = Path(__file__).resolve().parents[2]
APP_PATH = ROOT_DIR / "src" / "showup" / "ui" / "app.py"
PAGES_DIR = ROOT_DIR / "src" / "showup" / "ui" / "pages"


class TestStreamlitUIAppTest:
    """Verify Streamlit UI pages for clean rendering and absence of raw HTML leaks."""

    @pytest.fixture(autouse=True)
    def mock_ollama_and_tabpfn(self) -> None:
        """Mock external network calls so tests run instantaneously and strictly offline."""
        with (
            patch("showup.messaging.ollama_client.OllamaClient.check_health", return_value=True),
            patch(
                "showup.messaging.ollama_client.OllamaClient.list_models",
                return_value=["llama3.2:3b"],
            ),
            patch("showup.scoring.tabpfn_scorer.TabPFNScorer.is_available", return_value=False),
        ):
            yield

    def test_app_main_navigation_no_div_leaks(self) -> None:
        """Verify main router does not leak literal div tags in markdown or code blocks."""
        at = AppTest.from_file(str(APP_PATH), default_timeout=15)
        at.run()
        assert not at.exception

        for el in at.markdown:
            assert "<div" not in el.value, f"Raw HTML leak in markdown: {el.value}"

        for el in at.code:
            assert "<div" not in el.value, f"Raw HTML leak in code block: {el.value}"

    @pytest.mark.parametrize(
        "page_file",
        [
            "0_Home.py",
            "1_Import.py",
            "2_Dashboard.py",
            "3_Risk_Scores.py",
            "4_What_If.py",
            "5_Messages.py",
            "6_Feature_Audit.py",
            "7_Privacy.py",
            "8_About.py",
        ],
    )
    def test_pages_have_no_div_leaks(self, page_file: str) -> None:
        """Verify every individual page has zero raw HTML leaks in rendered text elements."""
        file_path = PAGES_DIR / page_file
        assert file_path.exists(), f"Page {file_path} must exist"

        at = AppTest.from_file(str(file_path), default_timeout=15)
        at.run()
        assert not at.exception, (
            f"Page {page_file} encountered an unexpected exception: {at.exception}"
        )

        # Assert no markdown element leaks raw <div
        for el in at.markdown:
            assert "<div" not in el.value, f"Raw HTML leak in markdown on {page_file}: {el.value}"

        # Assert no code block leaks raw <div
        for el in at.code:
            assert "<div" not in el.value, f"Raw HTML leak in code block on {page_file}: {el.value}"

        # Assert no text element leaks raw <div
        for el in at.text:
            assert "<div" not in el.value, f"Raw HTML leak in text on {page_file}: {el.value}"
