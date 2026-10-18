"""What-If analysis page: grounded intervention effects (deposits, confirmations)."""

from __future__ import annotations

import streamlit as st

from showup.insights.whatif import compute_grounded_whatif
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo
from showup.ui.components import (
    empty_state,
    load_sample_dataset,
    metric_card,
    page_header,
)

# 1. Header
page_header(
    title="Grounded 'What-If' Analysis",
    subtitle="Evaluate the empirical impact of deposits and confirmations on attendance. Calculated strictly from your records.",
    icon=":material/insights:",
)

with get_session() as session:
    labeled_bookings = BookingRepo.list_labeled(session)

# 2. Check sample size threshold
if len(labeled_bookings) < 15:
    empty_state(
        icon="⚖️",
        title="More Historical Data Required",
        message=(
            f"You currently have {len(labeled_bookings)} completed appointments. "
            "To provide honest, statistically grounded comparisons between bookings with "
            "and without interventions, at least 15 completed bookings are required."
        ),
    )

    sc1, sc2 = st.columns([1, 2])
    with sc1:
        if st.button("📥 Load Sample Data", type="primary", use_container_width=True):
            with st.spinner("Loading demo records..."):
                load_sample_dataset()
            st.rerun()
    with sc2:
        st.caption("Load 200 demo appointments to see full deposit and confirmation what-if cards immediately.")

else:
    cards = compute_grounded_whatif(labeled_bookings)

    col1, col2 = st.columns(2)

    # 1. Deposit Intervention Card
    with col1, st.container(border=True):
        st.subheader("💳 Upfront Deposits")
        dep = cards.get("deposit_paid") or cards.get("deposit")

        if dep and dep.is_visible and dep.difference_pp is not None:
            diff_sign = "+" if dep.difference_pp >= 0 else ""
            w_rate = f"{dep.with_show_rate * 100:.1f}%" if dep.with_show_rate is not None else "N/A"
            wo_rate = f"{dep.without_show_rate * 100:.1f}%" if dep.without_show_rate is not None else "N/A"

            metric_card(
                label="Show-Up Rate Difference",
                value=f"{diff_sign}{dep.difference_pp:.1f}%",
                help=f"{w_rate} with deposit vs {wo_rate} without",
            )

            st.markdown(
                f"**Sample Sizes:**\n"
                f"- With deposit: `{dep.with_count}` past bookings\n"
                f"- Without deposit: `{dep.without_count}` past bookings"
            )
        else:
            reason = (
                dep.factual_statement
                if dep
                else "Insufficient deposit variation to draw conclusions."
            )
            st.info(reason)

        st.warning(
            "⚠️ **Confounding Notice:** Clients willing to pay an upfront deposit often have higher commitment from the outset. "
            "Enforcing mandatory deposits may reduce overall booking volume even while lowering no-show rates."
        )

    # 2. Confirmation Reminder Card
    with col2, st.container(border=True):
        st.subheader("📲 Confirmation Requests")
        conf = cards.get("confirmed") or cards.get("confirmation")

        if conf and conf.is_visible and conf.difference_pp is not None:
            diff_sign = "+" if conf.difference_pp >= 0 else ""
            w_rate = f"{conf.with_show_rate * 100:.1f}%" if conf.with_show_rate is not None else "N/A"
            wo_rate = f"{conf.without_show_rate * 100:.1f}%" if conf.without_show_rate is not None else "N/A"

            metric_card(
                label="Show-Up Rate Difference",
                value=f"{diff_sign}{conf.difference_pp:.1f}%",
                help=f"{w_rate} confirmed vs {wo_rate} unconfirmed",
            )

            st.markdown(
                f"**Sample Sizes:**\n"
                f"- Confirmed: `{conf.with_count}` past bookings\n"
                f"- Unconfirmed: `{conf.without_count}` past bookings"
            )
        else:
            reason = (
                conf.factual_statement
                if conf
                else "Insufficient confirmation variation to draw conclusions."
            )
            st.info(reason)

        st.warning(
            "⚠️ **Confounding Notice:** Confirmed appointments naturally filter out clients who already plan to cancel. "
            "Confirmations help clarify intent, but sending reminders too late may not give you time to refill empty slots."
        )
