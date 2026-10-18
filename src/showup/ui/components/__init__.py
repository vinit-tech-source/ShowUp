"""UI components package."""

from showup.ui.components.widgets import (
    empty_state,
    get_system_model_status,
    load_sample_dataset,
    metric_card,
    page_header,
    render_empty_state,
    render_getting_started_checklist,
    render_metric_card,
    render_privacy_banner,
    render_risk_badge,
    safe_page_link,
    status_badge,
)
from showup.ui.theme import inject_custom_theme

__all__ = [
    "empty_state",
    "get_system_model_status",
    "inject_custom_theme",
    "load_sample_dataset",
    "metric_card",
    "page_header",
    "render_empty_state",
    "render_getting_started_checklist",
    "render_metric_card",
    "render_privacy_banner",
    "render_risk_badge",
    "safe_page_link",
    "status_badge",
]
