"""Reusable UI components for ShowUp Streamlit pages."""

from __future__ import annotations

import streamlit as st

from showup.domain.enums import RiskBand


def render_risk_badge(risk_band: RiskBand, probability: float | None = None) -> None:
    """Render a risk indicator badge with optional probability percentage."""
    badge_class = f"risk-badge-{risk_band.value.lower()}"
    prob_str = f" • {probability * 100:.0f}%" if probability is not None else ""
    icon = "🟢" if risk_band == RiskBand.LOW else ("🟡" if risk_band == RiskBand.MEDIUM else "🔴")

    st.markdown(
        f'<span class="risk-badge {badge_class}">{icon} {risk_band.value.upper()}{prob_str}</span>',
        unsafe_allow_html=True,
    )


def render_metric_card(
    title: str,
    value: str,
    subtext: str = "",
    delta: str | None = None,
) -> None:
    """Render a styled metric card."""
    delta_html = (
        f'<div style="color: #34d399; font-size: 0.8rem; margin-top: 0.2rem;">{delta}</div>'
        if delta
        else ""
    )
    subtext_html = f'<div class="metric-subtext">{subtext}</div>' if subtext else ""

    st.markdown(
        f"""
        <div class="showup-card">
            <div class="metric-label">{title}</div>
            <div class="metric-value">{value}</div>
            {delta_html}
            {subtext_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_privacy_banner() -> None:
    """Render the standard offline local-first privacy badge."""
    st.markdown(
        """
        <div class="privacy-banner">
            <span style="font-size: 1.25rem;">🔒</span>
            <div>
                <strong>Local-First & Zero Outbound Network:</strong>
                All CSV processing, risk scoring, and message drafting execute 100% locally on your machine.
                Client data never leaves your computer.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(
    title: str,
    description: str,
    icon: str = "📂",
) -> None:
    """Render an informative empty state card."""
    st.markdown(
        f"""
        <div class="showup-card" style="text-align: center; padding: 3rem 2rem;">
            <div style="font-size: 3rem; margin-bottom: 0.75rem;">{icon}</div>
            <h3 style="margin-bottom: 0.5rem; font-weight: 700;">{title}</h3>
            <p style="color: #94a3b8; max-width: 480px; margin: 0 auto 1.5rem auto;">
                {description}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
