"""Privacy page: local storage inspection and complete data wipe."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from showup.config import get_settings
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo, ClientRepo, wipe_all
from showup.ui.components import metric_card, page_header

# 1. Header
page_header(
    title="Privacy, Storage & Data Control",
    subtitle="Full transparency into where your records are stored and one-click data deletion.",
    icon=":material/lock:",
)

settings = get_settings()
db_file = Path(settings.db_path)
db_exists = db_file.exists()
db_size_kb = (db_file.stat().st_size / 1024.0) if db_exists else 0.0

with get_session() as session:
    client_count = len(ClientRepo.list_all(session))
    booking_count = len(BookingRepo.list_all(session))
    upcoming_count = len(BookingRepo.list_upcoming(session))

# 2. Plain Language Summary
st.subheader("Your Data on This Machine")
st.markdown(
    "All appointments, client profiles, and risk scores are stored in a private local database "
    "on this computer. ShowUp does not transmit your records to any external cloud service or server."
)

col1, col2, col3 = st.columns(3)
with col1:
    metric_card("Registered Clients", f"{client_count:,}", help="Total clients in local storage")
with col2:
    metric_card("Total Bookings", f"{booking_count:,}", help="All historical and scheduled visits")
with col3:
    metric_card("Upcoming Bookings", f"{upcoming_count:,}", help="Future schedule slots")

st.divider()

# 3. Technical expander
with st.expander("Advanced / technical details"):
    st.markdown(
        f"**Data Directory:** `{settings.data_dir}`\n\n"
        f"**Database File:** `{settings.db_path}`\n\n"
        f"**Database File Size:** `{db_size_kb:.1f} KB`\n\n"
        "**Access Control:** Local user permissions only. Zero outbound network socket connections permitted."
    )

st.divider()

# 4. Danger Zone: Wipe All Data
st.subheader("⚠️ Complete Data Wipe")
st.markdown(
    "Permanently deletes all imported clients, appointments, scoring results, and cached models from your local drive. "
    "This action cannot be undone."
)

confirm_wipe = st.checkbox("I understand that this will completely erase all my client and booking data.")

if st.button("🗑️ Erase All Data from Machine", type="primary", disabled=not confirm_wipe):
    with st.spinner("Purging database and local caches..."), get_session() as session:
        wipe_all(data_dir=settings.data_dir, session=session)
    st.success("All data has been completely erased from this machine.")
    st.rerun()
