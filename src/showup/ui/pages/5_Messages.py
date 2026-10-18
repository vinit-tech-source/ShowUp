"""Messages page: local LLM message drafting, manual review, and wa.me links."""

from __future__ import annotations

import streamlit as st

from showup.domain.enums import RiskBand
from showup.jobs.worker import get_scored_upcoming_ranked
from showup.messaging.guardrails import draft_message_with_guardrails
from showup.messaging.ollama_client import OllamaClient
from showup.messaging.templates import get_fallback_message
from showup.messaging.whatsapp import build_wa_link, clean_phone_number
from showup.storage.database import get_session
from showup.ui.components import (
    empty_state,
    load_sample_dataset,
    page_header,
    safe_page_link,
    status_badge,
)

# 1. Header
page_header(
    title="WhatsApp Message Center",
    subtitle="Draft polite, concise appointment reminders using local AI or deterministic templates. Nothing is ever auto-sent.",
    icon=":material/chat:",
)

with get_session() as session:
    upcoming_ranked = get_scored_upcoming_ranked(session)

# 2. Check empty state
if not upcoming_ranked:
    empty_state(
        icon="📱",
        title="No Upcoming Appointments to Message",
        message="Upload upcoming appointments via the Import page to draft confirmation messages, or load demo sample data.",
    )

    sc1, sc2 = st.columns([1, 2])
    with sc1:
        if st.button("📥 Load Sample Data", type="primary", use_container_width=True):
            with st.spinner("Loading demo records..."):
                load_sample_dataset()
            st.rerun()
    with sc2:
        st.caption("Loads 200 appointments with realistic upcoming slots ready for WhatsApp messaging.")

else:
    # 1. Ollama Health & Dynamic Model Status
    ollama_client = OllamaClient()
    ollama_ok = ollama_client.check_health()
    active_model_name = "Local AI"

    if ollama_ok:
        models = ollama_client.list_models()
        if models:
            active_model_name = models[0]
            st.success(f"🤖 **Local AI Active:** `{active_model_name}` running on `localhost:11434`.")
        else:
            st.warning("ℹ️ **Ollama Running:** No models currently installed. Built-in templates active.")
    else:
        st.info("ℹ️ **Offline Mode:** Ollama is offline. Curated multilingual fallback templates are active.")

    # Top Navigation back to Risk Scores
    bcol_nav, _ = st.columns([1.8, 3.2])
    with bcol_nav:
        safe_page_link(
            "pages/3_Risk_Scores.py",
            label="Back to Risk Scores",
            icon=":material/arrow_back:",
        )

    # 2. Select Appointment to Message
    booking_options = []
    booking_map = {}
    target_id = st.session_state.get("target_booking_id")
    default_idx = 0

    for idx, (booking, result, client) in enumerate(upcoming_ranked):
        band_str = f"[{result.risk_band.value.upper()}]" if result else "[UNSCORED]"
        name_str = client.name or "Client"
        time_str = booking.appointment_at.strftime("%b %d, %I:%M %p")
        label = f"{band_str} {name_str} — {booking.service_type} on {time_str}"
        booking_options.append(label)
        booking_map[label] = (booking, result, client)
        if target_id and str(booking.id) == target_id:
            default_idx = idx

    st.caption("💡 **How this works:** Select a client, review the polite draft below, and click the green WhatsApp button to send.")
    selected_label = st.selectbox("Select Upcoming Appointment", booking_options, index=default_idx)
    target_booking, target_result, target_client = booking_map[selected_label]

    # Target info display
    with st.container(border=True):
        tcol1, tcol2, tcol3 = st.columns(3, vertical_alignment="center")
        with tcol1:
            st.markdown(f"**Client:** {target_client.name or 'Unnamed'}")
            st.caption(f"Phone: {target_client.phone or 'Not provided'}")
        with tcol2:
            st.markdown(f"**Service:** {target_booking.service_type}")
            st.caption(f"Time: {target_booking.appointment_at.strftime('%A, %b %d at %I:%M %p')}")
        with tcol3:
            risk_band = target_result.risk_band if target_result else RiskBand.LOW
            status_badge(risk_band, target_result.probability if target_result else None)

    # 3. Drafting Controls
    st.subheader("Draft Confirmation Message")
    dcol1, dcol2 = st.columns([1, 2])
    with dcol1:
        lang_choice = st.selectbox(
            "Language",
            ["en", "hi", "mr"],
            format_func=lambda x: {"en": "English", "hi": "Hindi (हिन्दी)", "mr": "Marathi (मराठी)"}[x],
        )

    # Initialize draft state
    state_key = f"draft_{target_booking.id}_{lang_choice}"
    time_formatted = target_booking.appointment_at.strftime("%b %d at %I:%M %p")

    if state_key not in st.session_state:
        template_text = get_fallback_message(
            language_code=lang_choice,
            risk_band=risk_band,
            client_name=target_client.name,
            service_name=target_booking.service_type or "Appointment",
            appointment_time_str=time_formatted,
        )
        st.session_state[state_key] = template_text
        st.session_state[f"{state_key}_is_llm"] = False
        st.session_state[f"{state_key}_violations"] = []

    gen_btn = st.button("✨ Generate AI Draft (Local Model)", type="primary")

    if gen_btn:
        with st.spinner(f"Drafting with {active_model_name} and checking guardrails..."):
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
            st.session_state[f"{state_key}_violations"] = violations

    current_draft = st.session_state.get(state_key, "")
    is_llm = st.session_state.get(f"{state_key}_is_llm", False)
    violations = st.session_state.get(f"{state_key}_violations", [])

    source_badge = f"🤖 {active_model_name} Local AI" if is_llm else "📋 Curated Fallback Template"
    st.caption(f"Source: **{source_badge}** • Length: **{len(current_draft.split())} words**")

    if violations:
        with st.expander("🛡️ Guardrail Enforcement Notes"):
            for v in violations:
                st.caption(f"• {v}")

    # Editable text box
    edited_draft = st.text_area(
        "Message Text (Review and edit before sending)",
        value=current_draft,
        height=130,
        help="You have full editorial control. Nothing is ever sent automatically.",
    )

    # WhatsApp Link Generation
    st.divider()
    phone_clean = clean_phone_number(target_client.phone or "")

    if phone_clean:
        wa_url = build_wa_link(phone_clean, edited_draft)
        st.link_button(
            "📲 Review & Send via WhatsApp (wa.me)",
            wa_url,
            type="primary",
            help="Opens WhatsApp with this pre-filled message. You must still click send in WhatsApp.",
        )
        st.caption("🔒 Clicking this link opens WhatsApp with your pre-filled text. Nothing is auto-sent.")
    else:
        st.warning("Client has no phone number recorded. Copy the draft manually above to send via your messaging platform.")
