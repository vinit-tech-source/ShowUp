"""Import CSV page: upload, column mapping, validation, dry-run, and persistence."""

from __future__ import annotations

from uuid import UUID

import pandas as pd
import streamlit as st

from showup.domain.models import Booking
from showup.ingest.dedupe import dedupe_bookings
from showup.ingest.mapper import apply_mapping, suggest_mappings
from showup.ingest.reader import read_csv_safe
from showup.ingest.validator import validate_and_transform_df
from showup.jobs.worker import start_background_scoring
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo, ClientRepo
from showup.ui.components import (
    load_sample_dataset,
    page_header,
    render_getting_started_checklist,
    safe_page_link,
)

# 1. Header
page_header(
    title="Import Bookings CSV",
    subtitle="Upload past or upcoming appointment records. Client data is processed entirely on your machine.",
    icon=":material/upload_file:",
)

with get_session() as session:
    total_existing = len(BookingRepo.list_all(session))

# 2. File uploader
uploaded_file = st.file_uploader(
    "Select your appointments CSV file",
    type=["csv"],
    help="CSV file containing appointment records. Header names do not need to match standard names.",
)

# 3. If no file is uploaded, offer sample data and show checklist
if uploaded_file is None:
    if total_existing == 0:
        with get_session() as session:
            render_getting_started_checklist(session)

        st.divider()

    with st.container(border=True):
        st.markdown("### 💡 Don't have a CSV file ready?")
        st.caption(
            "Load our realistic demo dataset (200 appointments across 30 clients) to test "
            "risk prediction, cost analytics, and WhatsApp reminder drafting instantly."
        )
        if st.button("⚡ Load Demo Data (200 Appointments)", type="primary", use_container_width=True):
            with st.spinner("Generating and scoring realistic clinic sample data..."):
                count = load_sample_dataset()
            st.session_state["sample_loaded_count"] = count
            st.rerun()

    if st.session_state.get("sample_loaded_count") is not None:
        c = st.session_state["sample_loaded_count"]
        st.success(f"Successfully loaded and scored **{c} demo appointments**!")
        sc1, sc2 = st.columns(2)
        with sc1:
            safe_page_link(
                "pages/2_Dashboard.py",
                label="Open Business Dashboard",
                icon=":material/dashboard:",
                use_container_width=True,
            )
        with sc2:
            safe_page_link(
                "pages/3_Risk_Scores.py",
                label="View Upcoming Risk Scores",
                icon=":material/warning:",
                use_container_width=True,
            )

else:
    if st.session_state.get("last_uploaded_file") != uploaded_file.name:
        st.session_state["last_uploaded_file"] = uploaded_file.name
        st.session_state.pop("imported_count", None)

    content_bytes = uploaded_file.getvalue()

    try:
        df, detected_enc, detected_delim = read_csv_safe(content_bytes)
        delim_disp = repr(detected_delim)[1:-1]
        st.success(f"File loaded: **{len(df)} rows**, encoding **{detected_enc}**, delimiter **`{delim_disp}`**.")

        st.subheader("1. Map Columns")
        st.markdown("Match your CSV columns to ShowUp fields. Automatic suggestions are pre-selected.")

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
            m_client_name = st.selectbox("Client Name", col_opts, index=get_default_idx("client_name"))
            m_phone = st.selectbox("Phone Number", col_opts, index=get_default_idx("phone"))
            m_service = st.selectbox("Service Type", col_opts, index=get_default_idx("service_type"))
            m_price = st.selectbox("Price / Fee", col_opts, index=get_default_idx("price"))

        with col2:
            m_channel = st.selectbox("Booking Channel", col_opts, index=get_default_idx("channel"))
            m_deposit = st.selectbox("Deposit Paid", col_opts, index=get_default_idx("deposit_paid"))
            m_confirmed = st.selectbox("Confirmation Received", col_opts, index=get_default_idx("confirmed"))
            m_outcome = st.selectbox(
                "Outcome (attended / no-show)",
                col_opts,
                index=get_default_idx("outcome"),
                help="Historical result: attended, no_show, cancelled, or pending",
            )
            m_created_at = st.selectbox("Booking Created At", col_opts, index=get_default_idx("booking_created_at"))

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

        has_required_cols = bool(clean_mapping.get("client_id") and clean_mapping.get("appointment_datetime"))

        if not has_required_cols:
            st.warning("Please map both **Client Identifier** and **Appointment Date & Time** to proceed.")
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

            can_import = len(deduped_bookings) > 0
            act_col1, act_col2 = st.columns([1, 2])
            with act_col1:
                import_btn = st.button(
                    "🚀 Import Valid Bookings & Start Risk Scoring",
                    type="primary",
                    disabled=not can_import,
                    use_container_width=True,
                )

            with act_col2:
                if not can_import:
                    st.caption("No valid bookings available to import. Correct CSV errors to proceed.")

            if import_btn and can_import:
                with (
                    st.spinner("Saving to local database and starting scoring..."),
                    get_session() as session,
                ):
                    in_memory_to_persisted: dict[UUID, UUID] = {}
                    for c in clients:
                        persisted = ClientRepo.get_or_create(
                            session,
                            external_id=c.external_id,
                            name=c.name,
                            phone=c.phone,
                            language=c.language,
                            client_id=c.id,
                        )
                        in_memory_to_persisted[c.id] = persisted.id

                    existing_all = BookingRepo.list_all(session)
                    existing_set = {(b.client_id, b.appointment_at) for b in existing_all}

                    bookings_to_insert: list[Booking] = []
                    for b in deduped_bookings:
                        real_cid = in_memory_to_persisted.get(b.client_id, b.client_id)
                        if (real_cid, b.appointment_at) not in existing_set:
                            b_updated = Booking(
                                id=b.id,
                                client_id=real_cid,
                                appointment_at=b.appointment_at,
                                booking_created_at=b.booking_created_at,
                                service_type=b.service_type,
                                price=b.price,
                                channel=b.channel,
                                deposit_paid=b.deposit_paid,
                                confirmed=b.confirmed,
                                outcome=b.outcome,
                                source_file=b.source_file,
                                imported_at=b.imported_at,
                            )
                            bookings_to_insert.append(b_updated)
                            existing_set.add((real_cid, b.appointment_at))

                    if bookings_to_insert:
                        count = BookingRepo.add_batch(session, bookings_to_insert)
                        session.commit()
                    else:
                        count = 0

                    start_background_scoring()

                st.session_state["imported_count"] = count

            if st.session_state.get("imported_count") is not None:
                count = st.session_state["imported_count"]
                st.success(
                    f"Successfully imported **{count} bookings** into your local database! Background scoring initiated."
                )

                dash_col1, dash_col2 = st.columns(2)
                with dash_col1:
                    safe_page_link(
                        "pages/2_Dashboard.py",
                        label="Open Business Dashboard",
                        icon=":material/dashboard:",
                        use_container_width=True,
                    )

                with dash_col2:
                    safe_page_link(
                        "pages/3_Risk_Scores.py",
                        label="View Upcoming Risk Scores",
                        icon=":material/warning:",
                        use_container_width=True,
                    )

    except Exception as e:
        st.error(f"Error reading CSV file: {e}")
