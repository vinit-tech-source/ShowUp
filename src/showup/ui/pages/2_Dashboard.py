"""Dashboard page: deterministic cost report and scoring status overview."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from showup.insights.cost_report import compute_cost_report
from showup.scoring.tabpfn_scorer import TabPFNScorer
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo, ScoringRepo
from showup.ui.components import (
    empty_state,
    load_sample_dataset,
    metric_card,
    page_header,
    safe_page_link,
)

# 1. Header
page_header(
    title="Business Dashboard & Cost Report",
    subtitle="Factual analysis of what no-shows cost your business, calculated exclusively from your records.",
    icon=":material/dashboard:",
)

with get_session() as session:
    labeled_bookings = BookingRepo.list_labeled(session)
    upcoming_bookings = BookingRepo.list_upcoming(session)
    latest_run = ScoringRepo.get_latest_scoring_run(session)

# 2. Check if enough historical data exists
if len(labeled_bookings) < 10:
    empty_state(
        icon="📉",
        title="More Historical Data Needed",
        message=(
            f"You currently have {len(labeled_bookings)} completed appointments in ShowUp. "
            "A minimum of 10 completed appointments is required to compute honest, "
            "statistically meaningful cost and rate figures."
        ),
    )

    sc1, sc2 = st.columns([1, 2])
    with sc1:
        if st.button("📥 Load Sample Data", type="primary", use_container_width=True):
            with st.spinner("Loading demo records..."):
                load_sample_dataset()
            st.rerun()
    with sc2:
        st.caption("Load 200 demo appointments to see full monthly cost trends and metrics immediately.")

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

    # Top metric cards using native, accessible metric_card
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card(
            label="Total Bookings",
            value=f"{report.total_bookings:,}",
            help=f"{report.total_labeled} completed, {report.overall_no_show_count} unexcused no-shows",
        )
    with col2:
        metric_card(
            label="No-Show Rate",
            value=rate_val,
            help=f"Computed across {report.total_labeled} verified past visits",
        )
    with col3:
        metric_card(
            label="Total Lost Revenue",
            value=f"${report.total_lost_revenue:,.0f}",
            help="Direct lost billable service revenue from missed slots",
        )
    with col4:
        metric_card(
            label="Avg Monthly Loss",
            value=avg_loss_val,
            help=f"Average across {len(report.monthly_breakdown)} active month(s)",
        )

    st.divider()

    if upcoming_bookings:
        with st.container(border=True):
            d_col1, d_col2 = st.columns([2.0, 1.2], vertical_alignment="center")
            with d_col1:
                st.markdown(f"#### 🛡️ Next Step: Protect Your Upcoming Schedule ({len(upcoming_bookings)} Bookings)")
                st.caption("Prevent next month's losses before they happen. Review risk scores and send polite WhatsApp reminders.")
            with d_col2:
                safe_page_link(
                    "pages/3_Risk_Scores.py",
                    label="Review Risk Scores & Remind",
                    icon=":material/warning:",
                    use_container_width=True,
                )

    # Monthly Trends
    if report.monthly_breakdown:
        st.subheader("Monthly Cost & Attendance Breakdown")
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

# 3. Model Status Section
st.subheader("Risk Scoring Model Status")

scorer = TabPFNScorer()

if latest_run:
    baseline_model = "Calibrated Logistic Regression" if latest_run.tier == 2 else "Heuristic Rules"
    if latest_run.metrics_json and isinstance(latest_run.metrics_json, dict):
        baseline_model = str(latest_run.metrics_json.get("baseline_model", baseline_model))

    rcol1, rcol2, rcol3, rcol4 = st.columns(4)
    with rcol1:
        metric_card("Current Tier", f"Tier {latest_run.tier}")
    with rcol2:
        metric_card("Selected Model", latest_run.model_selected.upper())
    with rcol3:
        metric_card("Baseline Model", baseline_model)
    with rcol4:
        metric_card("Run Status", latest_run.status.value.capitalize())

    st.markdown("**Model Selection Rationale**")
    explanation_text = latest_run.explanation or "No explanation recorded."
    st.info(explanation_text)

    # Render backtest comparison table if present in metrics
    backtest_data = (
        latest_run.metrics_json.get("backtest")
        if isinstance(latest_run.metrics_json, dict)
        else None
    )
    if backtest_data and isinstance(backtest_data, dict):
        st.markdown("**Historical Backtest Comparison**")
        bt_rows = []
        for m_name, m_info in backtest_data.items():
            if isinstance(m_info, dict):
                bt_rows.append({
                    "Model": m_name.capitalize(),
                    "ROC-AUC": f"{m_info.get('roc_auc', 0.0):.3f}",
                    "95% Bootstrap CI": f"[{m_info.get('roc_auc_ci_low', 0.0):.3f} – {m_info.get('roc_auc_ci_high', 0.0):.3f}]",
                    "Brier Score": f"{m_info.get('brier_score', 0.0):.3f}",
                    "Role": "Selected" if m_name == latest_run.model_selected else ("Baseline" if m_name == "logistic" else "Candidate"),
                })
        if bt_rows:
            st.dataframe(pd.DataFrame(bt_rows), use_container_width=True, hide_index=True)

    if not scorer.is_available and latest_run.model_selected == "logistic":
        st.caption("ℹ️ Note: TabPFN library is not installed locally; ShowUp fell back to calibrated Logistic Regression.")
else:
    st.info("No scoring run has executed yet. Import upcoming bookings to score attendance risk.")
