"""Home page: overview metrics, guided workflow, hero call-to-action, and model status."""

from __future__ import annotations

import streamlit as st

from showup.domain.enums import RiskBand
from showup.jobs.worker import get_scored_upcoming_ranked
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo, ClientRepo, ScoringRepo
from showup.ui.components import (
    get_system_model_status,
    load_sample_dataset,
    metric_card,
    page_header,
    safe_page_link,
)

# 1. Page Header
page_header(
    title="ShowUp",
    subtitle="Local-first decision support to help solo service businesses eliminate appointment no-shows.",
    icon=":material/calendar_today:",
)

# 2. Database Counts & Scored Items
with get_session() as session:
    clients = ClientRepo.list_all(session)
    labeled = BookingRepo.list_labeled(session)
    upcoming = BookingRepo.list_upcoming(session)
    total_bookings = len(BookingRepo.list_all(session))
    latest_run = ScoringRepo.get_latest_scoring_run(session)
    scored_upcoming = get_scored_upcoming_ranked(session) if upcoming else []

high_risk_count = sum(1 for _, res, _ in scored_upcoming if res and res.risk_band == RiskBand.HIGH)
med_risk_count = sum(1 for _, res, _ in scored_upcoming if res and res.risk_band == RiskBand.MEDIUM)

if latest_run:
    scorer_name = latest_run.model_selected.upper()
    scorer_sub = f"Tier {latest_run.tier}"
else:
    scorer_name = "Awaiting"
    scorer_sub = "Ready to score"

# 3. Dynamic "What to do next" Action Banner
if total_bookings == 0:
    with st.container(border=True):
        bcol1, bcol2 = st.columns([2.0, 1.2], vertical_alignment="center")
        with bcol1:
            st.markdown("### 🚀 Welcome to ShowUp!")
            st.caption(
                "Stop losing revenue to appointment no-shows. Get started by uploading your appointment CSV "
                "(from Google Sheets, Calendly, or Fresha), or load realistic demo data with 1 click."
            )
        with bcol2:
            if st.button("⚡ Load Demo Data (200 Visits)", type="primary", use_container_width=True):
                with st.spinner("Generating and scoring realistic clinic sample data..."):
                    count = load_sample_dataset()
                st.success(f"Loaded and scored {count} demo bookings!")
                st.rerun()

elif upcoming and high_risk_count > 0:
    with st.container(border=True):
        acol1, acol2 = st.columns([1.9, 1.1], vertical_alignment="center")
        with acol1:
            st.markdown(
                f"### 🚨 Action Needed: **{high_risk_count} High-Risk Appointments**"
            )
            st.caption(
                f"ShowUp analyzed your booking habits and attendance history. "
                f"You have **{len(upcoming)} upcoming appointments** (🔴 {high_risk_count} High Risk • 🟡 {med_risk_count} Medium Risk). "
                "Send them polite WhatsApp confirmation reminders to protect your revenue."
            )
        with acol2:
            safe_page_link(
                "pages/3_Risk_Scores.py",
                label="Review High-Risk Bookings",
                icon=":material/warning:",
                use_container_width=True,
            )

elif upcoming:
    with st.container(border=True):
        acol1, acol2 = st.columns([1.9, 1.1], vertical_alignment="center")
        with acol1:
            st.markdown(
                f"### 🟢 Schedule Protected: **{len(upcoming)} Upcoming Bookings**"
            )
            st.caption(
                "All upcoming clients have low predicted no-show risk based on deposits, lead times, and attendance history."
            )
        with acol2:
            safe_page_link(
                "pages/3_Risk_Scores.py",
                label="View Upcoming Schedule",
                icon=":material/calendar_month:",
                use_container_width=True,
            )

st.divider()

# 4. Workspace Overview Metrics
st.subheader("Workspace Overview")
col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("Registered Clients", f"{len(clients):,}", help="Unique clients recorded in your local database")
with col2:
    metric_card("Historical Visits", f"{len(labeled):,}", help="Completed appointments used for pattern analysis")
with col3:
    metric_card("Upcoming Bookings", f"{len(upcoming):,}", help="Upcoming appointments evaluated for attendance risk")
with col4:
    metric_card("Active Scorer", scorer_name, help=scorer_sub)

st.divider()

# 5. Clear 3-Step Guided Workflow
st.subheader("Guided 3-Step Workflow")
st.caption("Everything you need to eliminate no-shows in 3 simple steps:")

gcol1, gcol2, gcol3 = st.columns(3)

with gcol1, st.container(border=True):
    st.markdown("#### 1. Import Bookings")
    st.caption("Upload your booking spreadsheet (CSV) or load synthetic clinic appointments.")
    if total_bookings > 0:
        st.success(f"✅ **{total_bookings:,}** bookings loaded")
    else:
        st.warning("⚠️ No appointments loaded yet")
    safe_page_link(
        "pages/1_Import.py",
        label="Open Importer",
        icon=":material/upload_file:",
        use_container_width=True,
    )

with gcol2, st.container(border=True):
    st.markdown("#### 2. Business Dashboard")
    st.caption("Inspect revenue lost to no-shows and review your honest model accuracy comparison.")
    if latest_run:
        st.success(f"✅ Evaluated with **{scorer_name}**")
    else:
        st.info("ℹ️ Awaiting scoring run")
    safe_page_link(
        "pages/2_Dashboard.py",
        label="Open Dashboard",
        icon=":material/dashboard:",
        use_container_width=True,
    )

with gcol3, st.container(border=True):
    st.markdown("#### 3. Risk & Reminders")
    st.caption("See who is likely to miss appointments. Draft polite, guardrailed messages with local AI.")
    if upcoming and high_risk_count > 0:
        st.error(f"⚠️ **{high_risk_count}** high-risk slots")
    elif upcoming:
        st.success(f"✅ **{len(upcoming)}** upcoming slots scored")
    else:
        st.info("ℹ️ No upcoming slots")
    safe_page_link(
        "pages/3_Risk_Scores.py",
        label="View Risk Scores",
        icon=":material/chat:",
        use_container_width=True,
    )

with st.expander("💡 Simple Guide: How does ShowUp work?"):
    st.markdown(
        """
        - **Step 1: Import your appointments** — Upload a CSV file exported from your booking system (Fresha, Calendly, Google Calendar, or Excel) on the **Import** page.
        - **Step 2: Understand your cost** — Check the **Dashboard** to see how much revenue no-shows cost your business each month and your overall no-show rate.
        - **Step 3: Stop no-shows before they happen** — Check **Risk Scores** to see upcoming clients ranked by risk. Click **Draft Message** to send a polite, 1-click WhatsApp confirmation before their slot.
        """
    )

st.divider()

# 6. Dynamic Local AI System Status
model_status = get_system_model_status()
with st.expander("Local AI & Model Status"):
    mcol1, mcol2 = st.columns(2)
    with mcol1:
        st.markdown(f"**WhatsApp Message Assistant:** {model_status['llm']}")
        st.caption("Inference runs strictly on your machine via local Ollama.")
    with mcol2:
        st.markdown(f"**Tabular Scoring Engine:** {model_status['tabpfn']}")
        if latest_run and latest_run.explanation:
            st.caption(f"Current selection rationale: {latest_run.explanation}")
        else:
            st.caption("Scoring engine selects the best model based on historical accuracy.")
