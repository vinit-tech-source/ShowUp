"""Privacy page: local storage inspection and complete data wipe."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from showup.config import get_settings
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo, ClientRepo, wipe_all
from showup.ui.components import inject_custom_theme, render_privacy_banner

inject_custom_theme()
render_privacy_banner()

st.title("🔒 Privacy, Storage & Data Control")
st.markdown("Full transparency into where your records are stored and one-click data deletion.")

settings = get_settings()
db_file = Path(settings.db_path)
db_exists = db_file.exists()
db_size_kb = (db_file.stat().st_size / 1024.0) if db_exists else 0.0

col1, col2 = st.columns(2)
with col1:
    st.subheader("📁 Local Storage Information")
    st.markdown(
        f"""
        <div class="showup-card">
            <strong>Data Directory:</strong><br>
            <code>{settings.data_dir}</code><br><br>
            <strong>SQLite Database File:</strong><br>
            <code>{settings.db_path}</code><br><br>
            <strong>Database Size:</strong> {db_size_kb:.1f} KB<br>
            <strong>WAL Mode:</strong> Enabled (high-concurrency local read/write)
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.subheader("📊 Current Database Counts")
    with get_session() as session:
        client_count = len(ClientRepo.list_all(session))
        booking_count = len(BookingRepo.list_all(session))
        upcoming_count = len(BookingRepo.list_upcoming(session))

    st.markdown(
        f"""
        <div class="showup-card">
            <strong>Unique Clients:</strong> {client_count:,}<br><br>
            <strong>Total Bookings:</strong> {booking_count:,}<br><br>
            <strong>Upcoming Appointments:</strong> {upcoming_count:,}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

# Danger Zone: Wipe All Data
st.subheader("⚠️ Complete Data Wipe")
st.markdown(
    "Permanently deletes all imported clients, appointments, scoring results, and cached models from your local drive. "
    "This action cannot be undone."
)

confirm_wipe = st.checkbox(
    "I understand that this will completely erase all my client and booking data."
)

if st.button("🗑️ Erase All Data from Machine", type="primary", disabled=not confirm_wipe):
    with st.spinner("Purging database and local caches..."), get_session() as session:
        wipe_all(data_dir=settings.data_dir, session=session)
    st.success("All data has been completely erased from this machine.")
    st.rerun()
