"""What-If analysis page: grounded intervention effects (deposits, confirmations)."""

from __future__ import annotations

import streamlit as st

from showup.insights.whatif import compute_grounded_whatif
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo
from showup.ui.components import (
    inject_custom_theme,
    render_empty_state,
    render_metric_card,
    render_privacy_banner,
)

inject_custom_theme()
render_privacy_banner()

st.title("💡 Grounded 'What-If' Analysis")
st.markdown(
    "Evaluate the empirical impact of deposits and confirmations on attendance. "
    "Calculated strictly from your own past appointment records — never hypothetical industry assumptions."
)

with get_session() as session:
    labeled_bookings = BookingRepo.list_labeled(session)

if len(labeled_bookings) < 15:
    render_empty_state(
        title="More Historical Data Required",
        description=(
            f"You currently have {len(labeled_bookings)} completed appointments. "
            f"To provide honest, statistically grounded comparisons between bookings with "
            f"and without interventions, at least 15 completed bookings are required."
        ),
        icon="⚖️",
    )
else:
    cards = compute_grounded_whatif(labeled_bookings)

    col1, col2 = st.columns(2)

    # 1. Deposit Intervention Card
    with col1:
        st.subheader("💳 Upfront Deposits")
        dep = cards.get("deposit")

        if dep and dep.is_visible and dep.difference_pp is not None:
            diff_sign = "+" if dep.difference_pp >= 0 else ""
            w_rate = f"{dep.with_show_rate * 100:.1f}%" if dep.with_show_rate is not None else "N/A"
            wo_rate = (
                f"{dep.without_show_rate * 100:.1f}%"
                if dep.without_show_rate is not None
                else "N/A"
            )
            render_metric_card(
                title="Show-Up Rate Difference",
                value=f"{diff_sign}{dep.difference_pp:.1f}%",
                subtext=f"{w_rate} with deposit vs {wo_rate} without",
            )
            st.markdown(
                f"""
                <div class="showup-card">
                    <strong>Sample Sizes:</strong><br>
                    • With deposit: <code>{dep.with_count}</code> past bookings<br>
                    • Without deposit: <code>{dep.without_count}</code> past bookings
                </div>
                """,
                unsafe_allow_html=True,
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
    with col2:
        st.subheader("📲 Confirmation Requests")
        conf = cards.get("confirmation")

        if conf and conf.is_visible and conf.difference_pp is not None:
            diff_sign = "+" if conf.difference_pp >= 0 else ""
            w_rate = (
                f"{conf.with_show_rate * 100:.1f}%" if conf.with_show_rate is not None else "N/A"
            )
            wo_rate = (
                f"{conf.without_show_rate * 100:.1f}%"
                if conf.without_show_rate is not None
                else "N/A"
            )
            render_metric_card(
                title="Show-Up Rate Difference",
                value=f"{diff_sign}{conf.difference_pp:.1f}%",
                subtext=f"{w_rate} confirmed vs {wo_rate} unconfirmed",
            )
            st.markdown(
                f"""
                <div class="showup-card">
                    <strong>Sample Sizes:</strong><br>
                    • Confirmed: <code>{conf.with_count}</code> past bookings<br>
                    • Unconfirmed: <code>{conf.without_count}</code> past bookings
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            reason = (
                conf.factual_statement
                if conf
                else "Insufficient confirmation variation to draw conclusions."
            )
            st.info(reason)

        st.caption(
            "💡 Proactive WhatsApp confirmation reminders allow clients to reschedule early if their plans change, "
            "opening up slots for other paying customers."
        )
