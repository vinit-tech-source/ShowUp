"""Curated deterministic fallback templates for appointment reminders.

Supports English (en), Hindi (hi), and Marathi (mr) across Low, Medium, and High risk bands.
All templates are guaranteed strictly <= 30 words, zero-guilt, and free of hallucinated numbers.
"""

from __future__ import annotations

from showup.domain.enums import RiskBand

TEMPLATES: dict[str, dict[RiskBand, str]] = {
    "en": {
        RiskBand.LOW: (
            "Hi {name}, just a friendly reminder of your {service} appointment "
            "scheduled for {time}. Looking forward to seeing you!"
        ),
        RiskBand.MEDIUM: (
            "Hi {name}, reminding you of your upcoming {service} appointment "
            "on {time}. Please reply if you need to adjust this time."
        ),
        RiskBand.HIGH: (
            "Hello {name}, your {service} appointment is reserved for {time}. "
            "Please reply YES to confirm your attendance. Thank you!"
        ),
    },
    "hi": {
        RiskBand.LOW: (
            "नमस्ते {name}, {time} पर आपकी {service} की बुकिंग याद दिलाने "
            "के लिए यह संदेश है। आपसे मिलने की प्रतीक्षा रहेगी!"
        ),
        RiskBand.MEDIUM: (
            "नमस्ते {name}, {time} पर आपकी {service} की बुकिंग है। "
            "यदि समय में बदलाव करना हो, तो कृपया इस संदेश का उत्तर दें।"
        ),
        RiskBand.HIGH: (
            "नमस्ते {name}, {time} पर आपकी {service} की बुकिंग निर्धारित है। "
            "कृपया अपनी उपस्थिति की पुष्टि के लिए इस संदेश का उत्तर दें। धन्यवाद!"
        ),
    },
    "mr": {
        RiskBand.LOW: (
            "नमस्कार {name}, तुमची {time} वाजता {service} साठी भेट निश्चित आहे. भेटण्याची वाट पाहत आहोत!"
        ),
        RiskBand.MEDIUM: (
            "नमस्कार {name}, तुमची {time} वाजता {service} साठी अपॉइंटमेंट आहे. "
            "वेळेत बदल करायचा असल्यास कृपया कळवा."
        ),
        RiskBand.HIGH: (
            "नमस्कार {name}, तुमची {time} वाजता {service} साठी भेट राखीव आहे. "
            "कृपया उपस्थिती निश्चित करण्यासाठी या संदेशास उत्तर द्या. धन्यवाद!"
        ),
    },
}

DEFAULT_NAMES: dict[str, str] = {
    "en": "there",
    "hi": "जी",
    "mr": "जी",
}


def get_fallback_message(
    language_code: str,
    risk_band: RiskBand,
    client_name: str | None,
    service_name: str,
    appointment_time_str: str,
) -> str:
    """Format a deterministic fallback message for the given risk band and language."""
    lang = language_code.lower().strip()
    if lang not in TEMPLATES:
        lang = "en"

    default_name = DEFAULT_NAMES.get(lang, "there")
    name = client_name.strip() if client_name and client_name.strip() else default_name
    service = service_name.strip() if service_name and service_name.strip() else "appointment"
    time_str = appointment_time_str.strip() if appointment_time_str else "your scheduled time"

    template = TEMPLATES[lang].get(risk_band, TEMPLATES[lang][RiskBand.LOW])
    return template.format(name=name, service=service, time=time_str)
