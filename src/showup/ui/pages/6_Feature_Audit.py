"""Feature audit page: allowlist inspection and privacy explanation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from showup.ui.components import page_header

# 1. Header
page_header(
    title="Feature Allowlist & Privacy Audit",
    subtitle="ShowUp enforces a strict behavioral feature allowlist. Demographic attributes are permanently excluded.",
    icon=":material/policy:",
)

st.subheader("The 14 Allowed Behavioral Features")
st.markdown(
    "Only behavioral, scheduling, and operational signals are fed to our models. "
    "Every variable is documented below in plain language."
)

FEATURE_DETAILS = [
    {
        "Feature Name": "lead_time_hours",
        "Category": "Scheduling",
        "Type": "Hours",
        "Description": "Hours elapsed between booking creation and scheduled appointment.",
    },
    {
        "Feature Name": "lead_time_bucket",
        "Category": "Scheduling",
        "Type": "Time category",
        "Description": "Discrete buckets: same day, 1-3 days, 3-7 days, 1-2 weeks, 2+ weeks.",
    },
    {
        "Feature Name": "day_of_week",
        "Category": "Scheduling",
        "Type": "Day of week (Monday–Sunday)",
        "Description": "Day of the week on which the appointment takes place.",
    },
    {
        "Feature Name": "hour_of_day",
        "Category": "Scheduling",
        "Type": "Hour of day (24-hour clock)",
        "Description": "Scheduled hour of appointment.",
    },
    {
        "Feature Name": "prior_visits",
        "Category": "Client History",
        "Type": "Count",
        "Description": "Number of attended past appointments for this client (strictly before target date).",
    },
    {
        "Feature Name": "prior_no_shows",
        "Category": "Client History",
        "Type": "Count",
        "Description": "Count of past no-shows for this client (strictly before target date).",
    },
    {
        "Feature Name": "prior_no_show_rate",
        "Category": "Client History",
        "Type": "Percentage (0%–100%)",
        "Description": "Historical no-show percentage for this client prior to target date.",
    },
    {
        "Feature Name": "is_new_client",
        "Category": "Client History",
        "Type": "Yes / No",
        "Description": "Yes if client has zero prior visits in database, No otherwise.",
    },
    {
        "Feature Name": "days_since_last_visit",
        "Category": "Client History",
        "Type": "Days count",
        "Description": "Days elapsed since client's most recent prior appointment.",
    },
    {
        "Feature Name": "booking_channel",
        "Category": "Operational",
        "Type": "Category",
        "Description": "How appointment was booked (online, phone, walk-in, referral).",
    },
    {
        "Feature Name": "service_type",
        "Category": "Operational",
        "Type": "Category",
        "Description": "Normalized service name (consultation, follow-up, etc.).",
    },
    {
        "Feature Name": "price",
        "Category": "Operational",
        "Type": "Fee amount",
        "Description": "Scheduled fee or price for the appointment.",
    },
    {
        "Feature Name": "deposit_paid",
        "Category": "Commitment",
        "Type": "Yes / No",
        "Description": "Whether an upfront deposit was secured.",
    },
    {
        "Feature Name": "confirmed",
        "Category": "Commitment",
        "Type": "Yes / No",
        "Description": "Whether client confirmed attendance via message or call.",
    },
]

df_features = pd.DataFrame(FEATURE_DETAILS)
st.dataframe(df_features, use_container_width=True, hide_index=True)

st.divider()

# 2. Excluded Attributes Table
st.subheader("Permanently Excluded & Prohibited Attributes")
st.markdown(
    "To prevent algorithmic bias and safeguard personal privacy, the following attributes "
    "are permanently quarantined during CSV upload and never used in risk scoring."
)

EXCLUDED_DETAILS = [
    {
        "Attribute": "Client Name",
        "Handling": "Quarantined in storage, never fed to models",
        "Ethical Rationale": "Prevents cultural or ethnic name bias in scoring algorithms.",
    },
    {
        "Attribute": "Phone Number / Email",
        "Handling": "Used solely for manual WhatsApp dispatch links",
        "Ethical Rationale": "Personal contact identifiers possess zero generalizable predictive value.",
    },
    {
        "Attribute": "Home Address / Postcode",
        "Handling": "Permanently stripped during CSV validation",
        "Ethical Rationale": "Prevents socioeconomic geographic redlining.",
    },
    {
        "Attribute": "Age / Gender / Demographic data",
        "Handling": "Rejected during CSV ingestion",
        "Ethical Rationale": "Protected legal characteristics. Attendance is determined by behavior, not identity.",
    },
]

df_excluded = pd.DataFrame(EXCLUDED_DETAILS)
st.dataframe(df_excluded, use_container_width=True, hide_index=True)

st.divider()

# 3. Technical expander
with st.expander("Advanced / technical details"):
    st.markdown(
        "**Leakage Prevention Architecture**:\n"
        "- All client history features (`prior_visits`, `prior_no_shows`) are computed strictly using records where `appointment_at < target_appointment_at`.\n"
        "- The feature matrix is validated against `ALLOWED_FEATURES` frozenset before feeding to model pipelines.\n"
        "- Missing numeric values are imputed with median historical training statistics."
    )
