"""Design system and CSS injection for ShowUp Streamlit UI.

Provides a premium, modern SaaS aesthetic supporting both light and dark modes:
- Plus Jakarta Sans & Inter typography
- Maximum content width of ~1100px with 8px rhythm
- Elevated glassmorphic metric cards and bordered containers
- Polished primary gradient buttons and interactive hover states
- Crisp dual-signaled risk pill badges
- Strict isolation using st.html to prevent markdown code block rendering bugs
"""

from __future__ import annotations

import streamlit as st


def inject_custom_theme() -> None:
    """Inject unified, theme-aware CSS into the Streamlit application."""
    css = """<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

/* Typography & Base Reset */
html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

h1, .stTitle {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.03em !important;
}

h2, h3, .stSubheader {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em !important;
}

/* Global Layout Constraints */
.stMainBlockContainer {
    max-width: 1100px !important;
    padding: 1.75rem 1.5rem 5rem 1.5rem !important;
    margin: 0 auto !important;
}

/* Elevated Metric Cards */
[data-testid="stMetric"] {
    background-color: var(--secondary-background-color) !important;
    border: 1px solid rgba(128, 128, 128, 0.18) !important;
    border-radius: 12px !important;
    padding: 1.15rem 1.35rem !important;
    box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.15) !important;
    transition: transform 0.2s cubic-bezier(0.4, 0, 0.2, 1),
                border-color 0.2s cubic-bezier(0.4, 0, 0.2, 1),
                box-shadow 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px) !important;
    border-color: rgba(99, 102, 241, 0.45) !important;
    box-shadow: 0 8px 24px -4px rgba(79, 70, 229, 0.22) !important;
}
[data-testid="stMetricLabel"] p {
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
    opacity: 0.78 !important;
}
[data-testid="stMetricValue"] div {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 1.7rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.025em !important;
}

/* Bordered Containers as Clean Cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: var(--secondary-background-color) !important;
    border: 1px solid rgba(128, 128, 128, 0.16) !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08) !important;
    padding: 1.15rem 1.35rem !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
    margin-bottom: 0.5rem !important;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: rgba(99, 102, 241, 0.3) !important;
}

/* Primary Button Styling */
.stButton > button[kind="primary"], .stButton > button[type="primary"] {
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 1.25rem !important;
    box-shadow: 0 4px 14px 0 rgba(79, 70, 229, 0.38) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}
.stButton > button[kind="primary"]:hover, .stButton > button[type="primary"]:hover {
    background: linear-gradient(135deg, #4338ca 0%, #4f46e5 100%) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px 0 rgba(79, 70, 229, 0.55) !important;
    border-color: rgba(255, 255, 255, 0.4) !important;
    color: #ffffff !important;
}

/* Secondary Button Styling - High Visibility */
.stButton > button:not([kind="primary"]):not([type="primary"]) {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 8px !important;
    color: #f8fafc !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.55rem 1.25rem !important;
    transition: all 0.2s ease !important;
}
.stButton > button:not([kind="primary"]):not([type="primary"]):hover {
    border-color: #818cf8 !important;
    color: #ffffff !important;
    background-color: rgba(99, 102, 241, 0.2) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.25) !important;
}

/* High-Visibility Page Link Buttons (Main Container Only) */
.stMainBlockContainer div[data-testid="stPageLink"] a,
.stMainBlockContainer a[data-testid="stPageLink-NavLink"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.5rem !important;
    background: linear-gradient(135deg, #4f46e5 0%, #6366f1 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 8px !important;
    padding: 0.55rem 1rem !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    text-decoration: none !important;
    box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    width: 100% !important;
    box-sizing: border-box !important;
    margin-top: 0.35rem !important;
}
.stMainBlockContainer div[data-testid="stPageLink"] a:hover,
.stMainBlockContainer a[data-testid="stPageLink-NavLink"]:hover {
    background: linear-gradient(135deg, #4338ca 0%, #4f46e5 100%) !important;
    color: #ffffff !important;
    border-color: #ffffff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(79, 70, 229, 0.6) !important;
}
.stMainBlockContainer div[data-testid="stPageLink"] a p,
.stMainBlockContainer a[data-testid="stPageLink-NavLink"] p {
    color: #ffffff !important;
    font-weight: 700 !important;
    margin: 0 !important;
    font-size: 0.9rem !important;
    line-height: 1.3 !important;
}
.stMainBlockContainer div[data-testid="stPageLink"] a svg,
.stMainBlockContainer a[data-testid="stPageLink-NavLink"] svg {
    fill: #ffffff !important;
    color: #ffffff !important;
}

/* Streamlit Link Button Styling */
a[data-testid="stLinkButton"] {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.5rem !important;
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 8px !important;
    padding: 0.65rem 1.4rem !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    text-decoration: none !important;
    box-shadow: 0 4px 14px rgba(34, 197, 94, 0.4) !important;
    transition: all 0.2s ease !important;
}
a[data-testid="stLinkButton"]:hover {
    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 22px rgba(34, 197, 94, 0.6) !important;
    color: #ffffff !important;
}
a[data-testid="stLinkButton"] p {
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    margin: 0 !important;
}

/* Sidebar Customization */
[data-testid="stSidebar"] {
    border-right: 1px solid rgba(128, 128, 128, 0.12) !important;
}
[data-testid="stSidebarNav"] a, [data-testid="stSidebar"] a {
    border-radius: 8px !important;
    padding: 0.45rem 0.75rem !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
[data-testid="stSidebarNav"] a:hover, [data-testid="stSidebar"] a:hover {
    background-color: rgba(128, 128, 128, 0.1) !important;
}
[data-testid="stSidebarNav"] a[aria-current="page"], [data-testid="stSidebar"] a[aria-current="page"] {
    background: linear-gradient(90deg, rgba(79, 70, 229, 0.18) 0%, rgba(99, 102, 241, 0.06) 100%) !important;
    border-left: 3px solid #6366f1 !important;
    font-weight: 600 !important;
}

/* Pill Badges with Dual Signaling */
.risk-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.28rem 0.75rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.risk-badge-low {
    background-color: rgba(16, 185, 129, 0.14);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.4);
}
.risk-badge-medium {
    background-color: rgba(245, 158, 11, 0.14);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.4);
}
.risk-badge-high {
    background-color: rgba(239, 68, 68, 0.14);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.4);
}

/* WhatsApp Link Button */
.wa-link-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
    background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
    color: #ffffff !important;
    font-weight: 600;
    font-size: 0.875rem;
    padding: 0.55rem 1.15rem;
    border-radius: 8px;
    text-decoration: none !important;
    box-shadow: 0 3px 12px rgba(34, 197, 94, 0.32);
    transition: all 0.2s ease;
}
.wa-link-btn:hover {
    background: linear-gradient(135deg, #16a34a 0%, #15803d 100%);
    transform: translateY(-1px);
    box-shadow: 0 5px 16px rgba(34, 197, 94, 0.45);
}

/* Form Inputs, Selectboxes, and Textarea */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] > div > div,
[data-testid="stTextArea"] textarea {
    border-radius: 8px !important;
    font-size: 0.9rem !important;
    transition: border-color 0.15s ease, box-shadow 0.15s ease !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stSelectbox"] > div > div:focus-within,
[data-testid="stTextArea"] textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.22) !important;
}

/* Alerts and Expanders */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    border-width: 1px !important;
}
[data-testid="stExpander"] {
    border-radius: 10px !important;
    border: 1px solid rgba(128, 128, 128, 0.18) !important;
    background-color: var(--secondary-background-color) !important;
}
</style>"""
    st.html(css)
