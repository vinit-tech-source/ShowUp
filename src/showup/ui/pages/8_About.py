"""About page: architecture, versions, licenses, and open-weight AI attributions."""

from __future__ import annotations

import streamlit as st

import showup
from showup.ui.components import get_system_model_status, page_header

# 1. Header
page_header(
    title="About ShowUp",
    subtitle="Open-weight, local-first decision support to help solo service businesses reduce appointment no-shows.",
    icon=":material/info:",
)

model_status = get_system_model_status()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Application Details")
    st.markdown(
        f"**ShowUp:** `v{showup.__version__}`\n\n"
        "**License:** MIT Open Source License\n\n"
        "**Privacy Guarantee:** 100% on-device operation. Zero telemetry."
    )

with col2:
    st.subheader("Local AI Models")
    st.markdown(
        f"**Message Assistant:** {model_status['llm']}\n\n"
        f"**Risk Scoring Engine:** {model_status['tabpfn']}\n\n"
        "**Supported Languages:** English, Hindi (हिन्दी), Marathi (मराठी)"
    )

st.divider()

# 2. Plain Language Attributions
st.subheader("Attributions & Acknowledgements")
st.markdown(
    """
    - **Uses TabPFN-2 by [Prior Labs](https://github.com/prior-labs/TabPFN)**: Pre-trained tabular foundation model. Permissive open-weight license (Apache 2.0 compatible) with attribution.
    - **Ollama & Open-Weights LLMs**: Local inference runtime enabling privacy-preserving reminder drafting.
    - **Scikit-learn**: Calibrated logistic regression and metrics evaluation.
    - **Streamlit**: Desktop web application interface.
    """
)

st.divider()

# 3. Technical Expander
with st.expander("Advanced / technical details"):
    st.markdown(
        f"**ShowUp Build:** `{showup.__version__}`\n\n"
        "**Python Runtime:** 3.12+ (strictly typed with mypy)\n\n"
        "**Offline Telemetry Guards:** `HF_HUB_DISABLE_TELEMETRY=1`, `DO_NOT_TRACK=1`, `TRANSFORMERS_OFFLINE=1`\n\n"
        "**Database Layer:** SQLite with SQLAlchemy 2 ORM and Alembic migrations."
    )
