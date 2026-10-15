"""Risk Scores page: scored upcoming bookings ranked by no-show risk."""

from __future__ import annotations

import streamlit as st

from showup.domain.enums import RiskBand
from showup.jobs.worker import (
    execute_scoring_job,
    get_scored_upcoming_ranked,
    is_scoring_in_progress,
)
from showup.storage.database import get_session
from showup.ui.components import (
    inject_custom_theme,
    render_empty_state,
    render_privacy_banner,
    render_risk_badge,
)

inject_custom_theme()
render_privacy_banner()

st.title("🎯 Upcoming Bookings & Risk Ranking")
st.markdown(
    "Upcoming appointments ranked by no-show risk. Identify high-risk slots before they cost you revenue."
)

# Scoring trigger
head_col1, head_col2 = st.columns([3, 1])
with head_col2:
    with get_session() as session:
        in_prog = is_scoring_in_progress(session)

    if in_prog:
        st.warning("⏳ Scoring currently in progress...")
    elif st.button("🔄 Re-Score Upcoming", type="primary", use_container_width=True):
        with st.spinner("Scoring bookings with local ML / rules engine..."):
            execute_scoring_job()
        st.success("Scoring complete!")
        st.rerun()

with get_session() as session:
    ranked_rows = get_scored_upcoming_ranked(session)

if not ranked_rows:
    render_empty_state(
        title="No Upcoming Bookings Found",
        description="There are currently no upcoming appointments scheduled in your database. Upload future appointments via the Import page.",
        icon="📅",
    )
else:
    # Summary metrics
    high_count = sum(1 for _, res, _ in ranked_rows if res and res.risk_band == RiskBand.HIGH)
    med_count = sum(1 for _, res, _ in ranked_rows if res and res.risk_band == RiskBand.MEDIUM)
    low_count = sum(1 for _, res, _ in ranked_rows if res and res.risk_band == RiskBand.LOW)
    unscored_count = sum(1 for _, res, _ in ranked_rows if res is None)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("🔴 High Risk", high_count)
    m2.metric("🟡 Medium Risk", med_count)
    m3.metric("🟢 Low Risk", low_count)
    m4.metric("Total Upcoming", len(ranked_rows))

    st.divider()

    # Filter & Search
    fcol1, fcol2 = st.columns([1, 2])
    with fcol1:
        band_filter = st.selectbox(
            "Filter by Risk Level",
            ["All Risk Levels", "High Risk Only", "Medium Risk Only", "Low Risk Only"],
        )
    with fcol2:
        search_query = st.text_input(
            "Search by Client Name or Service", placeholder="e.g. Sarah or Consultation"
        )

    # Filter rows
    filtered = []
    for booking, result, client in ranked_rows:
        band = result.risk_band if result else None

        if band_filter == "High Risk Only" and band != RiskBand.HIGH:
            continue
        if band_filter == "Medium Risk Only" and band != RiskBand.MEDIUM:
            continue
        if band_filter == "Low Risk Only" and band != RiskBand.LOW:
            continue

        if search_query:
            query = search_query.lower()
            name_match = client.name and query in client.name.lower()
            service_match = booking.service_type and query in booking.service_type.lower()
            if not (name_match or service_match):
                continue

        filtered.append((booking, result, client))

    st.markdown(f"**Showing {len(filtered)} appointment(s):**")

    for booking, result, client in filtered:
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 2, 2, 1.5])
            with c1:
                name_disp = client.name or "Unnamed Client"
                phone_disp = f" • {client.phone}" if client.phone else ""
                st.markdown(f"**{name_disp}**{phone_disp}")
                st.caption(f"Service: {booking.service_type or 'General'}")

            with c2:
                time_disp = booking.appointment_at.strftime("%b %d, %Y at %I:%M %p")
                st.markdown(f"🕒 **{time_disp}**")
                price_disp = f"${booking.price:.0f}" if booking.price is not None else "Unspecified"
                deposit_disp = " • Deposit Paid ✅" if booking.deposit_paid else ""
                st.caption(f"Price: {price_disp}{deposit_disp}")

            with c3:
                if result:
                    render_risk_badge(result.risk_band, result.probability)
                    st.caption(f"Model: {result.model_used.upper()}")
                else:
                    st.caption("Not yet scored")

            with c4:
                st.page_link(
                    "pages/5_Messages.py",
                    label="💬 Draft WhatsApp",
                    icon="📱",
                )

            if result and result.explanation:
                with st.expander("🔍 Risk Explanation & Contributing Factors"):
                    st.write(result.explanation)

            st.markdown(
                "<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid rgba(255,255,255,0.06);'>",
                unsafe_allow_html=True,
            )
