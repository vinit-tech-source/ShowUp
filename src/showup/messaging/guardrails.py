"""Message guardrails enforcing length, factual numbers, zero-guilt, and script verification."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from showup.domain.enums import RiskBand
from showup.logging_setup import get_logger
from showup.messaging.ollama_client import OllamaClient, OllamaError
from showup.messaging.prompt import build_draft_prompt
from showup.messaging.templates import get_fallback_message

logger = get_logger(__name__)

MAX_WORD_COUNT = 40

# Prohibited guilt words or coercive framing
BLOCKED_GUILT_WORDS = [
    r"\bmissed\b",
    r"\bno-?show\b",
    r"\bpenalty\b",
    r"\bpenalties\b",
    r"\bfine\b",
    r"\bfines\b",
    r"\bfee\b",
    r"\bcharged\b",
    r"\bloss\b",
    r"\blost\b",
    r"\bstrike\b",
    r"\bdeposit\b",
    r"\bforfeit\b",
    r"\bwaste\b",
    r"\bguarantee\b",
    r"\bwarning\b",
    r"\bblame\b",
    r"\bfault\b",
    r"\blast\s+time\b",
    r"\bagain\b",
]

# Patterns for prefixes commonly emitted by LLMs
PREFIX_PATTERNS = [
    r"^(?:WhatsApp\s*)?[Mm]essage\s*:\s*",
    r"^[Dd]raft\s*:\s*",
    r"^[Hh]ere\s+is\s+(?:the\s+)?message\s*:\s*",
    r"^[Ss]ubject\s*:\s*",
]

DEVANAGARI_REGEX = re.compile(r"[\u0900-\u097F]")


@dataclass(frozen=True)
class GuardrailResult:
    """Outcome of guardrail validation on a drafted message."""

    passed: bool
    violations: list[str] = field(default_factory=list)
    cleaned_text: str = ""


def clean_draft_text(text: str) -> str:
    """Strip extraneous quotes, prefixes, markdown wrappers, and trailing whitespace."""
    cleaned = text.strip()

    # Strip prefixes like "Message:" or "Here is the message:"
    for pattern in PREFIX_PATTERNS:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()

    # Strip surrounding quotation marks or markdown
    cleaned = cleaned.strip("\"'«»“”`*")

    # If markdown bold wrapped the whole string, strip it
    if cleaned.startswith("**") and cleaned.endswith("**") and len(cleaned) > 4:
        cleaned = cleaned[2:-2].strip()

    # Normalize multiple whitespace
    return re.sub(r"\s+", " ", cleaned).strip()


def verify_draft(
    text: str,
    allowed_digits: set[str],
    language_code: str = "en",
) -> GuardrailResult:
    """Validate that drafted text complies with all safety and truthfulness constraints.

    Never logs text or PII. Returns violation reasons if checks fail.
    """
    cleaned = clean_draft_text(text)
    violations: list[str] = []

    # 1. Non-empty check
    if not cleaned:
        violations.append("Draft message is empty.")
        return GuardrailResult(passed=False, violations=violations, cleaned_text=cleaned)

    # 2. Word count check (strictly <= 40 words)
    words = cleaned.split()
    if len(words) > MAX_WORD_COUNT:
        violations.append(
            f"Message exceeds maximum word count: {len(words)} words (limit: {MAX_WORD_COUNT})."
        )

    # 3. Allowed digits check (prevent hallucinated prices, phone numbers, addresses)
    digits_in_text = set(re.findall(r"\d", cleaned))
    unapproved_digits = digits_in_text - allowed_digits
    if unapproved_digits:
        violations.append(
            f"Message contains unapproved digits not present in input facts: "
            f"{sorted(unapproved_digits)}."
        )

    # 4. Prohibited guilt phrasing check
    lower_text = cleaned.lower()
    for pattern in BLOCKED_GUILT_WORDS:
        if re.search(pattern, lower_text):
            violations.append(f"Guilt or punitive language detected matching '{pattern}'.")

    # 5. Language script check
    lang = language_code.lower().strip()
    if lang in ("hi", "mr") and not DEVANAGARI_REGEX.search(cleaned):
        violations.append(
            f"Requested language '{lang}' requires Devanagari script, but none was detected."
        )

    passed = len(violations) == 0
    return GuardrailResult(passed=passed, violations=violations, cleaned_text=cleaned)


def draft_message_with_guardrails(
    ollama_client: OllamaClient,
    client_name: str | None,
    service_name: str,
    appointment_time_str: str,
    *,
    language_code: str = "en",
    risk_band: RiskBand = RiskBand.LOW,
    max_regenerations: int = 2,
) -> tuple[str, bool, list[str]]:
    """Draft an appointment confirmation message with Ollama, applying strict guardrails.

    If Ollama is unreachable, model is missing, or guardrails reject drafts after
    max_regenerations, falls back gracefully to a curated deterministic template.

    CRITICAL PRIVACY GUARANTEE: Neither client_name nor message text is logged.

    Returns:
        (message_text, is_llm_generated, violations_or_notes)
    """
    system_prompt, user_prompt, allowed_digits = build_draft_prompt(
        client_name=client_name,
        appointment_time_str=appointment_time_str,
        service_name=service_name,
        language_code=language_code,
        risk_band=risk_band,
    )

    all_violations: list[str] = []

    # Attempt generation with local Ollama
    for attempt in range(max_regenerations + 1):
        try:
            raw_output = ollama_client.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
            )
            result = verify_draft(raw_output, allowed_digits, language_code)
            if result.passed:
                logger.info(
                    "message_draft_approved",
                    attempt=attempt,
                    language=language_code,
                    risk_band=risk_band.value,
                )
                return result.cleaned_text, True, []

            # Guardrail triggered
            logger.warning(
                "message_guardrail_triggered",
                attempt=attempt,
                violation_count=len(result.violations),
                language=language_code,
            )
            all_violations.extend(result.violations)

        except OllamaError as e:
            logger.warning(
                "ollama_drafting_unavailable",
                error_type=type(e).__name__,
                attempt=attempt,
            )
            all_violations.append(f"Ollama unavailable: {type(e).__name__}")
            break
        except Exception as e:
            logger.warning(
                "unexpected_drafting_error",
                error_type=type(e).__name__,
                attempt=attempt,
            )
            all_violations.append(f"Draft error: {type(e).__name__}")
            break

    # Fall back to deterministic template
    logger.info(
        "message_fallback_selected",
        language=language_code,
        risk_band=risk_band.value,
        total_violations=len(all_violations),
    )
    fallback = get_fallback_message(
        language_code=language_code,
        risk_band=risk_band,
        client_name=client_name,
        service_name=service_name,
        appointment_time_str=appointment_time_str,
    )
    return fallback, False, all_violations
