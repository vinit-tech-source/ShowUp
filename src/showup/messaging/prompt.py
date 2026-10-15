"""Prompt builder for local Gemma message drafting via Ollama."""

from __future__ import annotations

import re

from showup.domain.enums import RiskBand

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "mr": "Marathi",
}

TONE_INSTRUCTIONS = {
    RiskBand.LOW: ("Tone: Friendly, brief, and warm. Standard upcoming appointment reminder."),
    RiskBand.MEDIUM: (
        "Tone: Warm and polite. Kindly request a quick reply if they need to adjust the time."
    ),
    RiskBand.HIGH: (
        "Tone: Courteous, professional, and clear. Emphasize confirming attendance "
        "to secure their reserved appointment time."
    ),
}


def build_draft_prompt(
    client_name: str | None,
    appointment_time_str: str,
    service_name: str,
    language_code: str = "en",
    risk_band: RiskBand = RiskBand.LOW,
) -> tuple[str, str, set[str]]:
    """Construct system prompt and user prompt for local LLM message generation.

    Returns:
        (system_prompt, user_prompt, allowed_digits_set)
    """
    lang_name = LANGUAGE_NAMES.get(language_code.lower().strip(), "English")
    name = client_name.strip() if client_name else "there"
    service = service_name.strip() if service_name else "appointment"
    time_str = appointment_time_str.strip()

    # Extract all digits present in the provided facts
    combined_facts = f"{name} {service} {time_str}"
    allowed_digits: set[str] = set(re.findall(r"\d", combined_facts))

    tone_guidance = TONE_INSTRUCTIONS.get(risk_band, TONE_INSTRUCTIONS[RiskBand.LOW])

    system_prompt = (
        f"You are a professional appointment scheduling assistant for a solo service business. "
        f"Draft a short, polite WhatsApp message in {lang_name} to confirm an upcoming booking.\n\n"
        f"CRITICAL CONSTRAINTS:\n"
        f"1. Length: STRICTLY under 40 words.\n"
        f"2. Language: Write entirely in {lang_name}.\n"
        f"3. Accuracy: You may ONLY use the exact client name, service, and time provided.\n"
        f"4. NEVER invent prices, fees, addresses, or phone numbers.\n"
        f"5. NO GUILT LANGUAGE: Never mention missing past appointments, penalties, "
        f"or lost income.\n"
        f"6. Output ONLY the message text. No greetings to the owner, no quotes, no markdown."
    )

    user_prompt = (
        f"Draft a WhatsApp message with these exact details:\n"
        f"- Client Name: {name}\n"
        f"- Service: {service}\n"
        f"- Appointment Time: {time_str}\n"
        f"- {tone_guidance}\n\n"
        f"Message:"
    )

    return system_prompt, user_prompt, allowed_digits
