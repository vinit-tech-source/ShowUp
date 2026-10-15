"""About page: architecture, versions, licenses, and open-weight AI attributions."""

from __future__ import annotations

import streamlit as st

import showup
from showup.ui.components import inject_custom_theme, render_privacy_banner

inject_custom_theme()
render_privacy_banner()

st.title("ℹ️ About ShowUp")
st.markdown(
    "ShowUp is an open-weight, local-first decision support tool for solo service businesses."
)

col1, col2 = st.columns(2)
with col1:
    st.subheader("📦 System Versions")
    st.markdown(
        f"""
        <div class="showup-card">
            <strong>ShowUp Core:</strong> <code>v{showup.__version__}</code><br>
            <strong>License:</strong> MIT License<br>
            <strong>Database:</strong> SQLite with Write-Ahead Logging (WAL)<br>
            <strong>Python:</strong> 3.12+ (Typed with mypy --strict)
        </div>
        """,
        unsafe_allow_html=True,
    )

with col2:
    st.subheader("🧠 Open-Weight AI Models")
    st.markdown(
        """
        <div class="showup-card">
            <strong>Scoring (Tier 2 ML):</strong><br>
            • TabPFN v2 (Prior Labs) — Tabular Foundation Model<br>
            • Calibrated Logistic Regression (Scikit-learn)<br><br>
            <strong>Drafting (WhatsApp LLM):</strong><br>
            • Gemma 2 via local Ollama (localhost:11434)<br>
            • Multi-lingual support: English, Hindi, Marathi
        </div>
        """,
        unsafe_allow_html=True,
    )

st.divider()

st.subheader("📜 Attributions & Licenses")
st.markdown(
    """
    - **TabPFN v2**: Developed by Prior Labs and the AutoML Freiburg team. Used for out-of-the-box in-context tabular prediction.
    - **Gemma 2**: Open-weights model by Google DeepMind. Run locally via Ollama.
    - **Scikit-learn**: BSD 3-Clause License.
    - **SQLAlchemy & Alembic**: MIT License.
    - **Streamlit**: Apache 2.0 License.
    - **Zero Telemetry Guarantee**: `HF_HUB_OFFLINE=1`, `DO_NOT_TRACK=1`, and `TRANSFORMERS_OFFLINE=1` are enforced at startup.
    """
)
