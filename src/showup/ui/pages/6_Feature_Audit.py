"""Feature audit page: allowlist inspection and privacy explanation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from showup.ui.components import inject_custom_theme, render_privacy_banner

inject_custom_theme()
render_privacy_banner()

st.title("🛡️ Feature Allowlist & Privacy Audit")
st.markdown(
    "ShowUp enforces a strict behavioral feature allowlist. "
    "Only 14 operational and historical signals are ever exposed to the machine learning models. "
    "All demographic and protected attributes are permanently stripped."
)

st.subheader("✅ The 14 Allowed Behavioral Features")

FEATURE_DETAILS = [
    {
        "Feature Name": "lead_time_hours",
        "Category": "Timing",
        "Type": "Numeric",
        "Description": "Hours elapsed between booking creation and scheduled appointment.",
    },
    {
        "Feature Name": "lead_time_bucket",
        "Category": "Timing",
        "Type": "Categorical",
        "Description": "Discrete buckets: same day, 1-3 days, 3-7 days, 1-2 weeks, 2+ weeks.",
    },
    {
        "Feature Name": "day_of_week",
        "Category": "Timing",
        "Type": "Numeric (0-6)",
        "Description": "Day of the week (Monday=0 to Sunday=6).",
    },
    {
        "Feature Name": "hour_of_day",
        "Category": "Timing",
        "Type": "Numeric (0-23)",
        "Description": "Scheduled hour of appointment (24-hour clock).",
    },
    {
        "Feature Name": "prior_visits",
        "Category": "Client History",
        "Type": "Numeric",
        "Description": "Count of attended prior appointments for this client (strictly before target date).",
    },
    {
        "Feature Name": "prior_no_shows",
        "Category": "Client History",
        "Type": "Numeric",
        "Description": "Count of past no-shows for this client (strictly before target date).",
    },
    {
        "Feature Name": "prior_no_show_rate",
        "Category": "Client History",
        "Type": "Float [0-1]",
        "Description": "Historical no-show percentage for this client prior to target date.",
    },
    {
        "Feature Name": "is_new_client",
        "Category": "Client History",
        "Type": "Binary (0/1)",
        "Description": "1 if client has zero prior visits in database, 0 otherwise.",
    },
    {
        "Feature Name": "days_since_last_visit",
        "Category": "Client History",
        "Type": "Numeric",
        "Description": "Days elapsed since client's most recent prior appointment.",
    },
    {
        "Feature Name": "booking_channel",
        "Category": "Operational",
        "Type": "Categorical",
        "Description": "How appointment was booked (online, phone, walk-in, instagram).",
    },
    {
        "Feature Name": "service_type",
        "Category": "Operational",
        "Type": "Categorical",
        "Description": "Normalized service name (consultation, follow-up, etc.).",
    },
    {
        "Feature Name": "price",
        "Category": "Operational",
        "Type": "Numeric",
        "Description": "Scheduled fee or price for the appointment.",
    },
    {
        "Feature Name": "deposit_paid",
        "Category": "Intervention",
        "Type": "Binary (0/1)",
        "Description": "Whether an upfront deposit was secured.",
    },
    {
        "Feature Name": "confirmation_received",
        "Category": "Intervention",
        "Type": "Binary (0/1)",
        "Description": "Whether client confirmed attendance prior to the slot.",
    },
]

st.dataframe(pd.DataFrame(FEATURE_DETAILS), use_container_width=True, hide_index=True)

st.divider()

st.subheader("🚫 Permanently Excluded Attributes")
st.markdown(
    "To eliminate algorithmic bias and safeguard personal privacy, the following attributes "
    "are **hard-blocked** and will cause an immediate error if introduced into the scoring model:"
)

EXCLUDED = [
    {
        "Attribute": "Age / Date of Birth",
        "Reason for Permanent Exclusion": "Demographic proxy. Age has no causal bearing on reliability; inclusion introduces ageism bias.",
    },
    {
        "Attribute": "Gender / Sex",
        "Reason for Permanent Exclusion": "Protected characteristic. Legally and ethically prohibited from influencing risk scores.",
    },
    {
        "Attribute": "Address / Zip Code / Neighborhood",
        "Reason for Permanent Exclusion": "Socioeconomic redlining proxy. Geolocation signals encode neighborhood-level bias.",
    },
    {
        "Attribute": "Client Name",
        "Reason for Permanent Exclusion": "PII and potential ethnic/cultural proxy. Used strictly for display and WhatsApp draft salutations.",
    },
    {
        "Attribute": "Phone Number / Email",
        "Reason for Permanent Exclusion": "PII. Used strictly for manual WhatsApp links. Never ingested as a model feature.",
    },
]

st.dataframe(pd.DataFrame(EXCLUDED), use_container_width=True, hide_index=True)
