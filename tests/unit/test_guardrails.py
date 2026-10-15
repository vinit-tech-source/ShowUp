"""Unit tests for message guardrails and fallback templates."""

from __future__ import annotations

from unittest.mock import patch

from showup.domain.enums import RiskBand
from showup.messaging.guardrails import (
    clean_draft_text,
    draft_message_with_guardrails,
    verify_draft,
)
from showup.messaging.ollama_client import OllamaClient, OllamaNotRunningError
from showup.messaging.templates import TEMPLATES, get_fallback_message


class TestCleanDraftText:
    def test_strip_prefixes(self) -> None:
        assert clean_draft_text("Message: Hello there!") == "Hello there!"
        assert clean_draft_text("WhatsApp Message: See you tomorrow.") == "See you tomorrow."
        assert clean_draft_text("Draft: Confirming your slot.") == "Confirming your slot."
        assert (
            clean_draft_text("Here is the message: Looking forward to it.")
            == "Looking forward to it."
        )

    def test_strip_quotes_and_markdown(self) -> None:
        assert clean_draft_text('"Hello John"') == "Hello John"
        assert clean_draft_text("'Hello John'") == "Hello John"
        assert clean_draft_text("“Hello John”") == "Hello John"
        assert clean_draft_text("**Hello John**") == "Hello John"
        assert clean_draft_text("`Hello John`") == "Hello John"


class TestVerifyDraft:
    def test_empty_text_fails(self) -> None:
        res = verify_draft("", allowed_digits={"1"})
        assert res.passed is False
        assert "empty" in res.violations[0].lower()

    def test_word_count_exceeded_fails(self) -> None:
        long_text = "word " * 45
        res = verify_draft(long_text, allowed_digits=set())
        assert res.passed is False
        assert any("maximum word count" in v for v in res.violations)

    def test_unapproved_digits_fails(self) -> None:
        # allowed digits: {1, 0}
        text = "Hi, your appointment is at 10 AM. Fee is 500 dollars."
        res = verify_draft(text, allowed_digits={"1", "0"})
        assert res.passed is False
        assert any("unapproved digits" in v for v in res.violations)

    def test_allowed_digits_passes(self) -> None:
        text = "Hi, your appointment is at 10 AM on the 10th."
        res = verify_draft(text, allowed_digits={"1", "0"})
        assert res.passed is True

    def test_blocked_guilt_phrases_fail(self) -> None:
        guilt_examples = [
            "We noticed you missed your last appointment.",
            "Please confirm so you are not a no-show.",
            "Late cancellations incur a 50 penalty fee.",
            "You will be charged if you do not come.",
            "This causes us a financial loss.",
        ]
        for example in guilt_examples:
            res = verify_draft(example, allowed_digits={"5", "0"})
            assert res.passed is False
            assert any("guilt or punitive" in v.lower() for v in res.violations)

    def test_devanagari_script_enforced_for_hi_and_mr(self) -> None:
        res_hi = verify_draft(
            "Hello John, your booking is confirmed.",
            allowed_digits=set(),
            language_code="hi",
        )
        assert res_hi.passed is False
        assert any("devanagari" in v.lower() for v in res_hi.violations)

        # Devanagari passes for Hindi
        devanagari_text = "नमस्ते जॉन, आपकी बुकिंग की पुष्टि की जाती है।"
        res_valid = verify_draft(devanagari_text, allowed_digits=set(), language_code="hi")
        assert res_valid.passed is True


class TestFallbackTemplates:
    def test_all_languages_and_bands_exist(self) -> None:
        for lang in ("en", "hi", "mr"):
            assert lang in TEMPLATES
            for band in (RiskBand.LOW, RiskBand.MEDIUM, RiskBand.HIGH):
                assert band in TEMPLATES[lang]
                msg = get_fallback_message(
                    language_code=lang,
                    risk_band=band,
                    client_name="TestClient",
                    service_name="TestService",
                    appointment_time_str="10:00 AM",
                )
                assert "TestClient" in msg
                assert "TestService" in msg
                assert "10:00 AM" in msg
                # Word count check
                assert len(msg.split()) <= 30

    def test_fallback_handles_none_client_name(self) -> None:
        msg = get_fallback_message(
            language_code="en",
            risk_band=RiskBand.LOW,
            client_name=None,
            service_name="Session",
            appointment_time_str="2 PM",
        )
        assert "there" in msg
        assert "Session" in msg


class TestDraftMessageWithGuardrails:
    def test_draft_accepted_when_llm_valid(self) -> None:
        client = OllamaClient()
        with patch.object(
            client,
            "generate",
            return_value="Hi Alice, looking forward to your session on Oct 12 at 2 PM!",
        ):
            msg, is_llm, violations = draft_message_with_guardrails(
                ollama_client=client,
                client_name="Alice",
                service_name="Consultation",
                appointment_time_str="Oct 12 at 2 PM",
                language_code="en",
                risk_band=RiskBand.LOW,
            )
            assert is_llm is True
            assert len(violations) == 0
            assert "Alice" in msg

    def test_draft_retries_and_falls_back_on_guilt_language(self) -> None:
        client = OllamaClient()
        # Returns guilt language every time
        with patch.object(
            client,
            "generate",
            return_value="Hi Alice, don't miss this appointment or you get a penalty fee!",
        ):
            msg, is_llm, violations = draft_message_with_guardrails(
                ollama_client=client,
                client_name="Alice",
                service_name="Consultation",
                appointment_time_str="Oct 12",
                language_code="en",
                risk_band=RiskBand.HIGH,
                max_regenerations=1,
            )
            # Must fall back to deterministic template
            assert is_llm is False
            assert "penalty" not in msg
            assert "Alice" in msg
            assert len(violations) > 0

    def test_draft_falls_back_when_ollama_not_running(self) -> None:
        client = OllamaClient()
        with patch.object(
            client,
            "generate",
            side_effect=OllamaNotRunningError("Ollama daemon offline"),
        ):
            msg, is_llm, violations = draft_message_with_guardrails(
                ollama_client=client,
                client_name="Bob",
                service_name="Haircut",
                appointment_time_str="3 PM",
                language_code="en",
                risk_band=RiskBand.MEDIUM,
            )
            assert is_llm is False
            assert "Bob" in msg
            assert "Haircut" in msg
            assert any("Ollama unavailable" in v for v in violations)
