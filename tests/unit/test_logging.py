"""Tests for showup.logging_setup — PII redaction and logger setup."""

from __future__ import annotations

from showup.logging_setup import get_logger, pii_redactor, setup_logging


class TestPiiRedactor:
    """Verify that PII is stripped from log event dicts."""

    def test_redacts_phone_numbers(self) -> None:
        event = {"event": "User called +91-9876543210 today"}
        result = pii_redactor(None, "", event)
        assert "+91-9876543210" not in result["event"]
        assert "[REDACTED_PHONE]" in result["event"]

    def test_redacts_email_addresses(self) -> None:
        event = {"event": "Contact user@example.com for details"}
        result = pii_redactor(None, "", event)
        assert "user@example.com" not in result["event"]
        assert "[REDACTED_EMAIL]" in result["event"]

    def test_redacts_name_key(self) -> None:
        event = {"event": "processing", "name": "John Doe"}
        result = pii_redactor(None, "", event)
        assert result["name"] == "[REDACTED]"

    def test_redacts_client_name_key(self) -> None:
        event = {"event": "scoring", "client_name": "Jane Smith"}
        result = pii_redactor(None, "", event)
        assert result["client_name"] == "[REDACTED]"

    def test_redacts_phone_key(self) -> None:
        event = {"event": "sending", "phone": "+1234567890"}
        result = pii_redactor(None, "", event)
        assert result["phone"] == "[REDACTED]"

    def test_redacts_message_content_key(self) -> None:
        event = {"event": "drafted", "message_content": "Hi John, reminder..."}
        result = pii_redactor(None, "", event)
        assert result["message_content"] == "[REDACTED]"

    def test_redacts_draft_text_key(self) -> None:
        event = {"event": "guardrail", "draft_text": "Your appointment is..."}
        result = pii_redactor(None, "", event)
        assert result["draft_text"] == "[REDACTED]"

    def test_preserves_safe_values(self) -> None:
        event = {"event": "scoring completed", "model": "logistic", "count": 42}
        result = pii_redactor(None, "", event)
        assert result["event"] == "scoring completed"
        assert result["model"] == "logistic"
        assert result["count"] == 42

    def test_redacts_multiple_phones_in_one_value(self) -> None:
        event = {"event": "numbers: +1234567890 and 9876543210"}
        result = pii_redactor(None, "", event)
        assert "+1234567890" not in result["event"]
        assert "9876543210" not in result["event"]

    def test_non_string_values_pass_through(self) -> None:
        event = {"event": "test", "count": 100, "active": True}
        result = pii_redactor(None, "", event)
        assert result["count"] == 100
        assert result["active"] is True


class TestSetupLogging:
    """Verify that logging can be configured without errors."""

    def test_setup_json_output(self) -> None:
        setup_logging(level="DEBUG", json_output=True)

    def test_setup_console_output(self) -> None:
        setup_logging(level="INFO", json_output=False)

    def test_get_logger_returns_bound_logger(self) -> None:
        setup_logging(level="DEBUG")
        logger = get_logger("test")
        assert logger is not None
