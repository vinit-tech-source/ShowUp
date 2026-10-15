"""Messaging module: local Ollama client, prompt builder, guardrails, templates, and wa.me links."""

from showup.messaging.guardrails import (
    GuardrailResult,
    clean_draft_text,
    draft_message_with_guardrails,
    verify_draft,
)
from showup.messaging.ollama_client import (
    ModelNotPulledError,
    OllamaClient,
    OllamaError,
    OllamaNotRunningError,
    OllamaTimeoutError,
)
from showup.messaging.prompt import (
    LANGUAGE_NAMES,
    build_draft_prompt,
)
from showup.messaging.templates import (
    TEMPLATES,
    get_fallback_message,
)
from showup.messaging.whatsapp import (
    build_wa_link,
    clean_phone_number,
)

__all__ = [
    "LANGUAGE_NAMES",
    "TEMPLATES",
    "GuardrailResult",
    "ModelNotPulledError",
    "OllamaClient",
    "OllamaError",
    "OllamaNotRunningError",
    "OllamaTimeoutError",
    "build_draft_prompt",
    "build_wa_link",
    "clean_draft_text",
    "clean_phone_number",
    "draft_message_with_guardrails",
    "get_fallback_message",
    "verify_draft",
]
