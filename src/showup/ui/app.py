"""ShowUp — Main Application Entry Point.

Run with:
    streamlit run src/showup/ui/app.py
"""

from __future__ import annotations

import streamlit as st

import showup
from showup.storage.database import get_session, init_db
from showup.storage.repositories import BookingRepo, ClientRepo, ScoringRepo
from showup.ui.components import (
    inject_custom_theme,
    render_metric_card,
    render_privacy_banner,
)

# 1. Initialize page configuration
st.set_page_config(
    page_title="ShowUp — Stop Appointment No-Shows",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Ensure database schema exists
init_db()

# 3. Inject custom CSS theme
inject_custom_theme()

# 4. Render privacy banner
render_privacy_banner()

# 5. Header section
st.title("✨ ShowUp")
st.markdown(
    "**Local-first decision support to help solo service businesses eliminate appointment no-shows.** "
    "All data, models, and inferences stay strictly on your device."
)

# 6. Overview Metrics
with get_session() as session:
    clients = ClientRepo.list_all(session)
    labeled = BookingRepo.list_labeled(session)
    upcoming = BookingRepo.list_upcoming(session)
    latest_run = ScoringRepo.get_latest_scoring_run(session)

col1, col2, col3, col4 = st.columns(4)
with col1:
    render_metric_card("Registered Clients", f"{len(clients):,}", "Clients in database")
with col2:
    render_metric_card("Historical Visits", f"{len(labeled):,}", "Used for model training")
with col3:
    render_metric_card("Upcoming Bookings", f"{len(upcoming):,}", "Active schedule")
with col4:
    model_disp = latest_run.model_selected.upper() if latest_run else "PENDING"
    tier_disp = f"Tier {latest_run.tier}" if latest_run else "Not yet scored"
    render_metric_card("Active Scorer", model_disp, tier_disp)

st.divider()

# 7. Navigation Quick Cards
st.subheader("🚀 Quick Actions")

qcol1, qcol2, qcol3 = st.columns(3)

with qcol1:
    st.markdown(
        """
        <div class="showup-card">
            <h4 style="margin-bottom: 0.5rem;">📥 1. Import Bookings</h4>
            <p style="color: #94a3b8; font-size: 0.9rem;">
                Upload your appointments CSV. ShowUp automatically sniffs formatting and matches columns.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_Import.py", label="Open CSV Importer", icon="📥")

with qcol2:
    st.markdown(
        """
        <div class="showup-card">
            <h4 style="margin-bottom: 0.5rem;">📊 2. View Cost Dashboard</h4>
            <p style="color: #94a3b8; font-size: 0.9rem;">
                See exactly what no-shows cost you in lost revenue each month based on your actual data.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/2_Dashboard.py", label="Open Dashboard", icon="📊")

with qcol3:
    st.markdown(
        """
        <div class="showup-card">
            <h4 style="margin-bottom: 0.5rem;">🎯 3. Score Upcoming Risk</h4>
            <p style="color: #94a3b8; font-size: 0.9rem;">
                Review upcoming appointments ranked by risk. Send polite WhatsApp reminders with 1-click.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Risk_Scores.py", label="View Risk Scores", icon="🎯")

# Sidebar summary
with st.sidebar:
    st.markdown(f"**ShowUp Core** `v{showup.__version__}`")
    st.markdown("🔒 **Local-first & Offline**")
    st.markdown("---")
    st.caption("Solo business decision support powered by open-weight AI (TabPFN v2 + Gemma 2).")
