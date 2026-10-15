"""Messages page: local LLM message drafting, manual review, and wa.me links."""

from __future__ import annotations

import streamlit as st

from showup.domain.enums import RiskBand
from showup.jobs.worker import get_scored_upcoming_ranked
from showup.messaging.guardrails import draft_message_with_guardrails
from showup.messaging.ollama_client import OllamaClient
from showup.messaging.whatsapp import build_wa_link, clean_phone_number
from showup.storage.database import get_session
from showup.ui.components import (
    inject_custom_theme,
    render_empty_state,
    render_privacy_banner,
    render_risk_badge,
)

inject_custom_theme()
render_privacy_banner()

st.title("💬 WhatsApp Message Center")
st.markdown(
    "Draft polite, concise appointment reminders using local Gemma or deterministic templates. "
    "**Nothing is ever auto-sent.** Review and send manually with a single click."
)

with get_session() as session:
    upcoming_ranked = get_scored_upcoming_ranked(session)

if not upcoming_ranked:
    render_empty_state(
        title="No Upcoming Appointments to Message",
        description="Upload upcoming appointments via the Import page to draft confirmation messages.",
        icon="📱",
    )
else:
    # 1. Ollama Health Status Check
    ollama_client = OllamaClient()
    ollama_ok = ollama_client.check_health()

    stat_col1, stat_col2 = st.columns([3, 1])
    with stat_col1:
        if ollama_ok:
            st.success("🤖 **Local Gemma AI Active:** Ollama is running on `localhost:11434`.")
        else:
            st.warning(
                "ℹ️ **Offline Mode:** Ollama is not running. Curated deterministic fallback templates will be used."
            )

    st.divider()

    # 2. Select Appointment to Message
    booking_options = []
    booking_map = {}
    for booking, result, client in upcoming_ranked:
        band_str = f"[{result.risk_band.value.upper()}]" if result else "[UNSCORED]"
        name_str = client.name or "Client"
        time_str = booking.appointment_at.strftime("%b %d, %I:%M %p")
        label = f"{band_str} {name_str} — {booking.service_type} on {time_str}"
        booking_options.append(label)
        booking_map[label] = (booking, result, client)

    selected_label = st.selectbox("Select Upcoming Appointment", booking_options)
    target_booking, target_result, target_client = booking_map[selected_label]

    # Target info box
    tcol1, tcol2, tcol3 = st.columns(3)
    with tcol1:
        st.markdown(f"**Client:** {target_client.name or 'Unnamed'}")
        st.caption(f"Phone: {target_client.phone or 'Not provided'}")
    with tcol2:
        st.markdown(f"**Service:** {target_booking.service_type}")
        st.caption(f"Time: {target_booking.appointment_at.strftime('%A, %b %d at %I:%M %p')}")
    with tcol3:
        risk_band = target_result.risk_band if target_result else RiskBand.LOW
        render_risk_badge(risk_band, target_result.probability if target_result else None)

    # 3. Drafting Controls
    st.subheader("Draft Message")
    dcol1, dcol2 = st.columns([1, 2])
    with dcol1:
        lang_choice = st.selectbox(
            "Language",
            ["en", "hi", "mr"],
            format_func=lambda x: {"en": "English", "hi": "Hindi (हिन्दी)", "mr": "Marathi (मराठी)"}[
                x
            ],
        )

    # Initialize draft state
    state_key = f"draft_{target_booking.id}_{lang_choice}"

    if st.button("✨ Generate / Refresh Draft", type="primary"):
        with st.spinner("Drafting with guardrails..."):
            time_formatted = target_booking.appointment_at.strftime("%b %d at %I:%M %p")
            draft_text, is_llm, violations = draft_message_with_guardrails(
                ollama_client=ollama_client,
                client_name=target_client.name,
                service_name=target_booking.service_type or "Appointment",
                appointment_time_str=time_formatted,
                language_code=lang_choice,
                risk_band=risk_band,
            )
            st.session_state[state_key] = draft_text
            st.session_state[f"{state_key}_is_llm"] = is_llm

    current_text = st.session_state.get(state_key, "")

    if current_text:
        is_llm = st.session_state.get(f"{state_key}_is_llm", False)
        source_badge = "🤖 Gemma 2 Local AI" if is_llm else "📋 Curated Fallback Template"
        st.caption(f"Generated via: **{source_badge}**")

        edited_text = st.text_area(
            "Review and edit message before sending:",
            value=current_text,
            height=120,
            key=f"text_{state_key}",
        )

        # Word count calculation
        word_count = len(edited_text.strip().split()) if edited_text.strip() else 0
        st.caption(f"Word count: **{word_count} / 40 words**")

        st.divider()

        # 4. Action: Manual WhatsApp Click
        phone_raw = target_client.phone or ""
        clean_p = clean_phone_number(phone_raw)

        wa_url = build_wa_link(clean_p, edited_text)

        st.markdown(
            f"""
            <a href="{wa_url}" target="_blank" class="wa-button">
                <span>💬</span> Open in WhatsApp ({clean_p or "Recipient Phone"})
            </a>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.info(
            "🛡️ **Safety Guarantee:** Clicking this link opens standard WhatsApp Web or desktop with your message pre-filled. "
            "ShowUp has zero access to send messages on your behalf."
        )
