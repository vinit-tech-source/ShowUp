"""WhatsApp wa.me click-to-chat URL generator.

ShowUp NEVER auto-sends messages. All communication requires manual owner
review and clicking the wa.me link directly.
"""

from __future__ import annotations

import re
import urllib.parse


def clean_phone_number(phone: str) -> str:
    """Normalize phone number to purely digits without spaces, hyphens, or leading plus.

    Examples:
        "+91 98765-43210" -> "919876543210"
        "(555) 123-4567"   -> "5551234567"
    """
    if not phone:
        return ""
    # Strip everything except digits
    return re.sub(r"\D", "", phone)


def build_wa_link(phone: str, message: str) -> str:
    """Construct a standard wa.me click-to-chat URL with properly URL-encoded text.

    Args:
        phone: Recipient phone number (international format preferred, e.g. "+91 9876543210").
        message: The reviewed text message content.

    Returns:
        Clickable wa.me URL.
    """
    digits_only = clean_phone_number(phone)
    encoded_text = urllib.parse.quote(message)

    if digits_only:
        return f"https://wa.me/{digits_only}?text={encoded_text}"
    return f"https://wa.me/?text={encoded_text}"
