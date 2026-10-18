"""ShowUp — Main Application Router & Shell.

Configures global layout, responsive theme, explicit st.navigation, and offline sidebar footer.
"""

from __future__ import annotations

import streamlit as st

import showup
from showup.storage.database import init_db
from showup.ui.theme import inject_custom_theme

# 1. Initialize global page configuration
st.set_page_config(
    page_title="ShowUp",
    page_icon=":material/calendar_today:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Ensure database schema exists
init_db()

# 3. Inject unified theme and CSS constraints
inject_custom_theme()

# 4. Explicit page navigation definition
pages = [
    st.Page("pages/0_Home.py", title="Home", icon=":material/home:", default=True),
    st.Page("pages/1_Import.py", title="Import", icon=":material/upload_file:"),
    st.Page("pages/2_Dashboard.py", title="Dashboard", icon=":material/dashboard:"),
    st.Page("pages/3_Risk_Scores.py", title="Risk Scores", icon=":material/warning:"),
    st.Page("pages/4_What_If.py", title="What-If", icon=":material/insights:"),
    st.Page("pages/5_Messages.py", title="Messages", icon=":material/chat:"),
    st.Page("pages/6_Feature_Audit.py", title="Feature Audit", icon=":material/policy:"),
    st.Page("pages/7_Privacy.py", title="Privacy", icon=":material/lock:"),
    st.Page("pages/8_About.py", title="About", icon=":material/info:"),
]

nav = st.navigation(pages)

# 5. Compact, centralized offline privacy banner in sidebar footer
with st.sidebar:
    st.markdown("---")
    st.caption(":material/lock: **Runs offline.** Your data stays on this computer.")
    st.caption(f"ShowUp `v{showup.__version__}`")

# 6. Run active page
nav.run()
