"""Dashboard page: deterministic cost report and scoring status overview."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from showup.insights.cost_report import compute_cost_report
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo, ScoringRepo
from showup.ui.components import (
    inject_custom_theme,
    render_empty_state,
    render_metric_card,
    render_privacy_banner,
)

inject_custom_theme()
render_privacy_banner()

st.title("📊 Business Dashboard & Cost Report")
st.markdown(
    "Factual analysis of what no-shows cost your business, calculated exclusively from your records."
)

with get_session() as session:
    labeled_bookings = BookingRepo.list_labeled(session)
    latest_run = ScoringRepo.get_latest_scoring_run(session)

if len(labeled_bookings) < 10:
    render_empty_state(
        title="More Historical Data Needed",
        description=(
            f"You currently have {len(labeled_bookings)} completed appointments in ShowUp. "
            f"A minimum of 10 completed appointments is required to compute honest, "
            f"statistically meaningful cost and rate figures."
        ),
        icon="📉",
    )
    st.info("💡 Head to the **Import** page to upload your historical bookings CSV.")
else:
    report = compute_cost_report(labeled_bookings)

    rate_val = (
        f"{report.overall_no_show_rate * 100.0:.1f}%"
        if report.overall_no_show_rate is not None
        else "N/A"
    )
    avg_loss_val = (
        f"${report.average_monthly_lost_revenue:,.0f}"
        if report.average_monthly_lost_revenue is not None
        else "N/A"
    )

    # Top metric cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_metric_card(
            title="Total Bookings",
            value=f"{report.total_bookings:,}",
            subtext=f"{report.total_labeled} completed, {report.overall_no_show_count} no-shows",
        )
    with col2:
        render_metric_card(
            title="No-Show Rate",
            value=rate_val,
            subtext=f"Computed across {report.total_labeled} past visits",
        )
    with col3:
        render_metric_card(
            title="Total Lost Revenue",
            value=f"${report.total_lost_revenue:,.0f}",
            subtext="Direct lost billable service revenue",
        )
    with col4:
        render_metric_card(
            title="Avg Monthly Loss",
            value=avg_loss_val,
            subtext=f"Across {len(report.monthly_breakdown)} active month(s)",
        )

    st.divider()

    # Monthly Trends
    if report.monthly_breakdown:
        st.subheader("📅 Monthly Cost & Attendance Breakdown")
        month_rows = []
        for m in report.monthly_breakdown:
            m_rate = f"{m.no_show_rate * 100.0:.1f}%" if m.no_show_rate is not None else "N/A"
            month_rows.append(
                {
                    "Month": m.year_month,
                    "Total Bookings": m.total_bookings,
                    "Attended": m.attended_count,
                    "No-Shows": m.no_show_count,
                    "No-Show Rate": m_rate,
                    "Lost Revenue": f"${m.lost_revenue:,.2f}",
                }
            )
        df_months = pd.DataFrame(month_rows)
        st.dataframe(df_months, use_container_width=True, hide_index=True)

st.divider()

# Scoring Engine Status Section
st.subheader("🤖 Risk Scoring Model Status")
if latest_run:
    rcol1, rcol2, rcol3 = st.columns(3)
    rcol1.metric("Current Tier", f"Tier {latest_run.tier}")
    rcol2.metric("Selected Model", latest_run.model_selected.upper())
    rcol3.metric("Status", latest_run.status.value.capitalize())

    st.markdown(
        f"""
        <div class="showup-card" style="margin-top: 1rem;">
            <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.35rem;">MODEL SELECTION RATIONALE</div>
            <div style="font-size: 0.95rem; line-height: 1.5;">{latest_run.explanation or "No explanation recorded."}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.info("No scoring run has executed yet. Import upcoming bookings to score attendance risk.")
