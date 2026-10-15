"""Unit tests for Ollama client, prompt construction, and WhatsApp links."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from showup.domain.enums import RiskBand
from showup.messaging.ollama_client import (
    ModelNotPulledError,
    OllamaClient,
    OllamaNotRunningError,
    OllamaTimeoutError,
)
from showup.messaging.prompt import build_draft_prompt
from showup.messaging.whatsapp import build_wa_link, clean_phone_number


class TestOllamaClient:
    def test_health_check_true_when_ok(self) -> None:
        client = OllamaClient(base_url="http://localhost:11434")
        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp

            assert client.check_health() is True

    def test_health_check_false_on_connection_error(self) -> None:
        client = OllamaClient(base_url="http://localhost:11434")
        with patch("httpx.Client.get", side_effect=httpx.ConnectError("Offline")):
            assert client.check_health() is False

    def test_list_models_returns_names(self) -> None:
        client = OllamaClient()
        with patch("httpx.Client.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "models": [{"name": "gemma2:2b"}, {"name": "llama3:latest"}]
            }
            mock_get.return_value = mock_resp

            models = client.list_models()
            assert "gemma2:2b" in models
            assert "llama3:latest" in models

    def test_list_models_raises_when_offline(self) -> None:
        client = OllamaClient()
        with (
            patch("httpx.Client.get", side_effect=httpx.ConnectError("Offline")),
            pytest.raises(OllamaNotRunningError),
        ):
            client.list_models()

    def test_is_model_available(self) -> None:
        client = OllamaClient()
        with patch.object(client, "list_models", return_value=["gemma2:2b", "gemma2:9b"]):
            assert client.is_model_available("gemma2:2b") is True
            assert client.is_model_available("gemma2") is True
            assert client.is_model_available("mistral") is False

    def test_generate_success(self) -> None:
        client = OllamaClient()
        with patch("httpx.Client.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"response": "Hi John, see you tomorrow at 10 AM!"}
            mock_post.return_value = mock_resp

            text = client.generate("Please remind John", model="gemma2:2b")
            assert "see you tomorrow" in text

    def test_generate_raises_model_not_pulled_on_404(self) -> None:
        client = OllamaClient()
        with patch("httpx.Client.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 404
            mock_post.return_value = mock_resp

            with pytest.raises(ModelNotPulledError):
                client.generate("prompt", model="unknown_model")

    def test_generate_raises_timeout(self) -> None:
        client = OllamaClient()
        with (
            patch("httpx.Client.post", side_effect=httpx.ReadTimeout("Timeout")),
            pytest.raises(OllamaTimeoutError),
        ):
            client.generate("prompt", max_retries=1)


class TestPromptBuilder:
    def test_build_draft_prompt_en_low_risk(self) -> None:
        sys_p, usr_p, digits = build_draft_prompt(
            client_name="Sarah",
            appointment_time_str="Oct 15 at 10:30 AM",
            service_name="Physio Consultation",
            language_code="en",
            risk_band=RiskBand.LOW,
        )
        assert "Sarah" in usr_p
        assert "Physio Consultation" in usr_p
        assert "10:30 AM" in usr_p
        assert "Friendly, brief, and warm" in usr_p
        assert "STRICTLY under 40 words" in sys_p
        assert digits == {"1", "5", "0", "3"}

    def test_build_draft_prompt_hi_high_risk(self) -> None:
        sys_p, usr_p, digits = build_draft_prompt(
            client_name="Rajesh",
            appointment_time_str="14:00",
            service_name="Driving Lesson",
            language_code="hi",
            risk_band=RiskBand.HIGH,
        )
        assert "Hindi" in sys_p
        assert "Rajesh" in usr_p
        assert "confirming attendance" in usr_p
        assert digits == {"1", "4", "0"}


class TestWhatsAppLinks:
    def test_clean_phone_number(self) -> None:
        assert clean_phone_number("+91 98765-43210") == "919876543210"
        assert clean_phone_number("(555) 123-4567") == "5551234567"
        assert clean_phone_number("") == ""

    def test_build_wa_link(self) -> None:
        link = build_wa_link("+91 98765 43210", "Hello John, see you at 10:00 AM!")
        assert link.startswith("https://wa.me/919876543210?text=")
        assert "Hello%20John" in link
        assert "10%3A00%20AM%21" in link

    def test_build_wa_link_empty_phone(self) -> None:
        link = build_wa_link("", "Reminder text")
        assert link == "https://wa.me/?text=Reminder%20text"
