"""Custom styling and CSS injection for ShowUp Streamlit UI.

Provides high-end modern dark-mode aesthetic with Inter typography,
glassmorphic card containers, tailored risk badges, and subtle micro-animations.
"""

from __future__ import annotations

import streamlit as st


def inject_custom_theme() -> None:
    """Inject polished custom CSS into the Streamlit application."""
    css = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Global Typography & Background */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at 15% 15%, #0f172a 0%, #090d16 100%);
        color: #f1f5f9;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #0d1322 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }

    /* Cards & Containers */
    .showup-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        backdrop-filter: blur(8px);
        margin-bottom: 1rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .showup-card:hover {
        border-color: rgba(99, 102, 241, 0.4);
        transform: translateY(-2px);
    }

    /* Metric Display */
    .metric-value {
        font-size: 2.25rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        line-height: 1.1;
        background: linear-gradient(135deg, #ffffff 30%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94a3b8;
        margin-bottom: 0.35rem;
    }
    .metric-subtext {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 0.25rem;
    }

    /* Badges */
    .risk-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .risk-badge-low {
        background: rgba(16, 185, 129, 0.15);
        color: #34d399;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .risk-badge-medium {
        background: rgba(245, 158, 11, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .risk-badge-high {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    /* Banner / Callout */
    .privacy-banner {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 10px;
        padding: 0.85rem 1.25rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        color: #cbd5e1;
        font-size: 0.875rem;
        margin-bottom: 1.5rem;
    }

    /* WhatsApp Link Button */
    .wa-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white !important;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.6rem 1.25rem;
        border-radius: 8px;
        text-decoration: none !important;
        box-shadow: 0 4px 12px rgba(37, 211, 102, 0.3);
        transition: all 0.2s ease;
    }
    .wa-button:hover {
        box-shadow: 0 6px 20px rgba(37, 211, 102, 0.45);
        transform: translateY(-1px);
    }

    /* Monospace facts */
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.85rem;
    }

    /* Streamlit Button Tweaks */
    button[kind="primary"] {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
        border: none !important;
        font-weight: 600 !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
