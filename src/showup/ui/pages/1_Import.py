"""Import CSV page: upload, column mapping, validation, dry-run, and persistence."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from showup.ingest.dedupe import dedupe_bookings
from showup.ingest.mapper import apply_mapping, suggest_mappings
from showup.ingest.reader import read_csv_safe
from showup.ingest.validator import validate_and_transform_df
from showup.jobs.worker import start_background_scoring
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo, ClientRepo
from showup.ui.components import inject_custom_theme, render_privacy_banner

inject_custom_theme()
render_privacy_banner()

st.title("📥 Import Bookings CSV")
st.markdown(
    "Upload past or upcoming appointment records. Client data is processed entirely on your machine."
)

uploaded_file = st.file_uploader(
    "Select your appointments CSV file",
    type=["csv"],
    help="CSV file containing appointment records. Header names do not need to match standard names.",
)

if uploaded_file is not None:
    content_bytes = uploaded_file.getvalue()

    try:
        df, detected_enc, detected_delim = read_csv_safe(content_bytes)
        st.success(
            f"File loaded successfully: **{len(df)} rows**, "
            f"encoding **{detected_enc}**, delimiter **`{repr(detected_delim)[1:-1]}`**."
        )

        st.subheader("1. Map Columns")
        st.markdown(
            "Match your CSV columns to ShowUp fields. Automatic suggestions are pre-selected."
        )

        headers = list(df.columns)
        suggested = suggest_mappings(headers)

        col_opts = ["(None / Skip)", *headers]

        def get_default_idx(field_name: str) -> int:
            matched = suggested.get(field_name)
            if matched and matched in headers:
                return headers.index(matched) + 1
            return 0

        col1, col2 = st.columns(2)
        with col1:
            m_client_id = st.selectbox(
                "Client Identifier *",
                col_opts,
                index=get_default_idx("client_id"),
                help="Unique ID, phone number, or name identifying the client (required)",
            )
            m_app_at = st.selectbox(
                "Appointment Date & Time *",
                col_opts,
                index=get_default_idx("appointment_datetime"),
                help="Date and time of appointment (required)",
            )
            m_client_name = st.selectbox(
                "Client Name",
                col_opts,
                index=get_default_idx("client_name"),
            )
            m_phone = st.selectbox(
                "Phone Number",
                col_opts,
                index=get_default_idx("phone"),
            )
            m_service = st.selectbox(
                "Service Type",
                col_opts,
                index=get_default_idx("service_type"),
            )
            m_price = st.selectbox(
                "Price / Fee",
                col_opts,
                index=get_default_idx("price"),
            )

        with col2:
            m_channel = st.selectbox(
                "Booking Channel",
                col_opts,
                index=get_default_idx("channel"),
            )
            m_deposit = st.selectbox(
                "Deposit Paid",
                col_opts,
                index=get_default_idx("deposit_paid"),
            )
            m_confirmed = st.selectbox(
                "Confirmation Received",
                col_opts,
                index=get_default_idx("confirmed"),
            )
            m_outcome = st.selectbox(
                "Outcome (attended / no-show)",
                col_opts,
                index=get_default_idx("outcome"),
                help="Historical result: attended, no_show, cancelled, or pending",
            )
            m_created_at = st.selectbox(
                "Booking Created At",
                col_opts,
                index=get_default_idx("booking_created_at"),
            )

        def clean_val(v: str) -> str | None:
            return None if v == "(None / Skip)" else v

        mapping_dict = {
            "client_id": clean_val(m_client_id),
            "appointment_datetime": clean_val(m_app_at),
            "client_name": clean_val(m_client_name),
            "phone": clean_val(m_phone),
            "service_type": clean_val(m_service),
            "price": clean_val(m_price),
            "channel": clean_val(m_channel),
            "deposit_paid": clean_val(m_deposit),
            "confirmed": clean_val(m_confirmed),
            "outcome": clean_val(m_outcome),
            "booking_created_at": clean_val(m_created_at),
        }
        clean_mapping = {k: v for k, v in mapping_dict.items() if v is not None}

        st.divider()
        st.subheader("2. Validation & Dry Run")

        if not clean_mapping.get("client_id") or not clean_mapping.get("appointment_datetime"):
            st.warning(
                "Please map both **Client Identifier** and **Appointment Date & Time** to proceed."
            )
        else:
            mapped_df = apply_mapping(df, clean_mapping)
            clients, bookings, val_report = validate_and_transform_df(
                mapped_df, source_file=uploaded_file.name
            )
            deduped_bookings, dup_count = dedupe_bookings(bookings)

            stat1, stat2, stat3 = st.columns(3)
            stat1.metric("Valid Rows", len(deduped_bookings))
            stat2.metric("Invalid Rows", val_report.error_rows)
            stat3.metric("Duplicates Filtered", dup_count)

            if val_report.errors:
                with st.expander(f"⚠️ View {len(val_report.errors)} Validation Errors"):
                    err_rows = [
                        {"Row": e.row_index, "Field": e.field, "Issue": e.message}
                        for e in val_report.errors[:50]
                    ]
                    st.dataframe(pd.DataFrame(err_rows), use_container_width=True)

            if deduped_bookings:
                st.markdown("**Preview of First 5 Sanitized Records:**")
                preview_data = [
                    {
                        "Client": b.client_id,
                        "Time": b.appointment_at.isoformat(),
                        "Service": b.service_type,
                        "Price": b.price,
                        "Outcome": b.outcome.value if b.outcome else "pending",
                    }
                    for b in deduped_bookings[:5]
                ]
                st.dataframe(pd.DataFrame(preview_data), use_container_width=True)

                st.divider()
                st.subheader("3. Commit to Database")

                if st.button("🚀 Import Valid Bookings & Start Risk Scoring", type="primary"):
                    with st.spinner("Saving to local SQLite database..."):
                        with get_session() as session:
                            # Save clients
                            for c in clients:
                                ClientRepo.get_or_create(
                                    session,
                                    external_id=c.external_id,
                                    name=c.name,
                                    phone=c.phone,
                                    language=c.language,
                                )

                            count = BookingRepo.add_batch(session, deduped_bookings)
                            session.commit()

                        # Kick off background scoring job
                        start_background_scoring()

                        st.success(
                            f"Successfully imported **{count} bookings** into your local database! "
                            f"Background scoring initiated."
                        )
                        st.info(
                            "👉 Check the **Dashboard** or **Risk Scores** pages to explore your insights."
                        )

    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
