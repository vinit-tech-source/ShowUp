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
    empty_state,
    load_sample_dataset,
    metric_card,
    page_header,
    status_badge,
)

# 1. Header
page_header(
    title="Upcoming Bookings & Risk Ranking",
    subtitle="Upcoming appointments ranked by no-show risk. Identify high-risk slots before they cost you revenue.",
    icon=":material/warning:",
)

with get_session() as session:
    in_prog = is_scoring_in_progress(session)
    ranked_rows = get_scored_upcoming_ranked(session)

has_upcoming = len(ranked_rows) > 0

# 2. Scoring Action Bar
head_col1, head_col2 = st.columns([2, 1])
with head_col2:
    if in_prog:
        st.warning("⏳ Scoring currently in progress...")
    else:
        score_btn = st.button(
            "🔄 Re-Score Upcoming",
            type="primary",
            disabled=not has_upcoming,
            use_container_width=True,
        )
        if not has_upcoming:
            st.caption("No upcoming bookings to score — import bookings first.")

        if score_btn and has_upcoming:
            with st.spinner("Scoring bookings with local ML / rules engine..."):
                execute_scoring_job()
            st.success("Scoring complete!")
            st.rerun()

# 3. Empty State if no upcoming bookings
if not has_upcoming:
    empty_state(
        icon="📅",
        title="No Upcoming Bookings Found",
        message="There are currently no upcoming appointments scheduled in your database. Upload future appointments via the Import page, or load sample data.",
    )

    sc1, sc2 = st.columns([1, 2])
    with sc1:
        if st.button("📥 Load Sample Data", type="primary", use_container_width=True):
            with st.spinner("Loading demo bookings..."):
                load_sample_dataset()
            st.rerun()
    with sc2:
        st.caption("Load 200 demo appointments to see full risk scores immediately.")

else:
    # Summary metrics
    high_count = sum(1 for _, res, _ in ranked_rows if res and res.risk_band == RiskBand.HIGH)
    med_count = sum(1 for _, res, _ in ranked_rows if res and res.risk_band == RiskBand.MEDIUM)
    low_count = sum(1 for _, res, _ in ranked_rows if res and res.risk_band == RiskBand.LOW)

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card("High Risk", f"{high_count}", help="Priority slots needing attention")
    with m2:
        metric_card("Medium Risk", f"{med_count}", help="Short notice or unconfirmed")
    with m3:
        metric_card("Low Risk", f"{low_count}", help="Reliable repeat clients")
    with m4:
        metric_card("Total Upcoming", f"{len(ranked_rows)}", help="Total active schedule")

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
            "Search Client or Service",
            placeholder="e.g. Sarah, Massage, Consultation",
        )

    # Filter and sort rows (High -> Medium -> Low, then by probability descending)
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

    st.markdown(f"**Showing {len(filtered)} scheduled appointment(s):**")
    st.caption("💡 **Tip:** Click **💬 Remind** on any appointment to instantly draft and send a polite WhatsApp confirmation message.")

    # Table Header
    h1, h2, h3, h4, h5, h6 = st.columns([1.9, 1.9, 1.8, 1.5, 2.3, 1.6])
    h1.caption("**TIME**")
    h2.caption("**CLIENT**")
    h3.caption("**SERVICE**")
    h4.caption("**RISK BAND**")
    h5.caption("**SUGGESTED ACTION**")
    h6.caption("**ACTION**")

    st.markdown("---")

    for booking, result, client in filtered:
        with st.container(border=True):
            c1, c2, c3, c4, c5, c6 = st.columns(
                [1.9, 1.9, 1.8, 1.5, 2.3, 1.6],
                vertical_alignment="center",
            )

            time_str = booking.appointment_at.strftime("%b %d • %I:%M %p")
            c1.markdown(f"**{time_str}**")

            client_name = client.name or "Client"
            c2.markdown(f"**{client_name}**")
            if client.phone:
                c2.caption(client.phone)

            price_str = f"${booking.price:.0f}" if booking.price is not None else ""
            c3.markdown(f"{booking.service_type}")
            if price_str:
                c3.caption(price_str)

            if result:
                with c4:
                    status_badge(result.risk_band, result.probability)

                if result.risk_band == RiskBand.HIGH:
                    c5.markdown("🚨 **Request deposit / confirmation**")
                elif result.risk_band == RiskBand.MEDIUM:
                    c5.markdown("⚠️ Send friendly reminder")
                else:
                    c5.markdown("✅ Standard check-in")
            else:
                c4.caption("Unscored")
                c5.caption("Run scoring")

            with c6:
                if st.button(
                    "💬 Remind",
                    key=f"btn_remind_{booking.id}",
                    type="primary",
                    use_container_width=True,
                    help=f"Draft WhatsApp reminder for {client_name}",
                ):
                    st.session_state["target_booking_id"] = str(booking.id)
                    st.switch_page("pages/5_Messages.py")

            if result and result.explanation:
                with st.expander("Details & Behavioral Factors"):
                    st.caption(result.explanation)
