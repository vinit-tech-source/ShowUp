"""Reusable, high-quality UI components for ShowUp Streamlit pages.

Strictly avoids multi-line indented markdown strings to guarantee no raw HTML leaks.
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID

import streamlit as st

from showup.domain.enums import RiskBand
from showup.domain.models import Booking
from showup.ingest.dedupe import dedupe_bookings
from showup.ingest.validator import validate_and_transform_df
from showup.jobs.worker import execute_scoring_job
from showup.messaging.ollama_client import OllamaClient
from showup.scoring.tabpfn_scorer import TabPFNScorer
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo, ClientRepo, ScoringRepo
from showup.synthetic.generator import generate_synthetic_dataset

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def page_header(title: str, subtitle: str, icon: str | None = None) -> None:
    """Render a consistent page header with clear hierarchy and one-line purpose."""
    full_title = f"{icon} {title}" if icon else title
    st.title(full_title)
    st.markdown(f"*{subtitle}*")


def metric_card(
    label: str,
    value: str,
    help: str | None = None,  # noqa: A002
    delta: str | None = None,
) -> None:
    """Render a native, accessible metric card."""
    st.metric(label=label, value=value, delta=delta, help=help)


def empty_state(
    icon: str,
    title: str,
    message: str,
    action_label: str | None = None,
    on_action: Callable[[], None] | None = None,
) -> None:
    """Render a structured empty state container with an optional action button."""
    st.info(f"**{icon} {title}**\n\n{message}")
    if action_label and on_action and st.button(action_label, type="primary"):
        on_action()


def status_badge(risk_band: RiskBand, probability: float | None = None) -> None:
    """Render a risk indicator badge with explicit color, icon, and text label."""
    prob_str = f" • {probability * 100:.0f}%" if probability is not None else ""
    icon = ":material/check_circle:" if risk_band == RiskBand.LOW else (
        ":material/schedule:" if risk_band == RiskBand.MEDIUM else ":material/error:"
    )

    st.markdown(f"{icon} **{risk_band.value.upper()}{prob_str}**")


def get_system_model_status() -> dict[str, str]:
    """Dynamically detect installed Ollama model and scoring model readiness."""
    # 1. Ollama LLM detection
    client = OllamaClient()
    ollama_online = client.check_health()
    if ollama_online:
        installed_models = client.list_models()
        if installed_models:
            active_model = installed_models[0]
            llm_status = f"{active_model} (Active via Ollama)"
        else:
            llm_status = "Ollama active (No models pulled)"
    else:
        llm_status = "Offline (Curated templates active)"

    # 2. TabPFN Scorer detection
    scorer = TabPFNScorer()
    if scorer.is_available:
        tabpfn_status = "TabPFN-2"
    else:
        tabpfn_status = scorer.fallback_reason or "Fallback: Calibrated Logistic Regression active"

    return {
        "llm": llm_status,
        "tabpfn": tabpfn_status,
        "ollama_online": "Online" if ollama_online else "Offline",
    }


def load_sample_dataset() -> int:
    """Generate and persist 200 synthetic appointments across 30 clients and score them."""
    df = generate_synthetic_dataset(n_clients=30, n_bookings=200, seed=42)
    clients, bookings, _ = validate_and_transform_df(df, source_file="demo_sample.csv")
    deduped, _ = dedupe_bookings(bookings)

    with get_session() as session:
        in_memory_to_persisted: dict[UUID, UUID] = {}
        for c in clients:
            persisted = ClientRepo.get_or_create(
                session,
                external_id=c.external_id,
                name=c.name,
                phone=c.phone,
                language=c.language,
                client_id=c.id,
            )
            in_memory_to_persisted[c.id] = persisted.id

        existing_all = BookingRepo.list_all(session)
        existing_set = {(b.client_id, b.appointment_at) for b in existing_all}

        bookings_to_insert: list[Booking] = []
        for b in deduped:
            real_cid = in_memory_to_persisted.get(b.client_id, b.client_id)
            if (real_cid, b.appointment_at) not in existing_set:
                b_updated = Booking(
                    id=b.id,
                    client_id=real_cid,
                    appointment_at=b.appointment_at,
                    booking_created_at=b.booking_created_at,
                    service_type=b.service_type,
                    price=b.price,
                    channel=b.channel,
                    deposit_paid=b.deposit_paid,
                    confirmed=b.confirmed,
                    outcome=b.outcome,
                    source_file=b.source_file,
                    imported_at=b.imported_at,
                )
                bookings_to_insert.append(b_updated)
                existing_set.add((real_cid, b.appointment_at))

        if bookings_to_insert:
            BookingRepo.add_batch(session, bookings_to_insert)
            session.commit()

    # Automatically score the loaded sample data
    execute_scoring_job()
    return len(deduped)


def render_getting_started_checklist(session: Session) -> None:
    """Render a 3-step checklist ticking off as the user completes actions."""
    total_bookings = len(BookingRepo.list_all(session))
    latest_run = ScoringRepo.get_latest_scoring_run(session)
    upcoming = BookingRepo.list_upcoming(session)

    step1_done = total_bookings > 0
    step2_done = latest_run is not None
    step3_done = len(upcoming) > 0 and step2_done

    st.subheader("Getting Started")

    c1, c2, c3 = st.columns(3)
    with c1, st.container(border=True):
        s1_icon = "✅" if step1_done else "1️⃣"
        st.markdown(f"**{s1_icon} Import Bookings**")
        if step1_done:
            st.caption(f"{total_bookings} appointments loaded")
        else:
            st.caption("Upload CSV or load sample data")

    with c2, st.container(border=True):
        s2_icon = "✅" if step2_done else "2️⃣"
        st.markdown(f"**{s2_icon} Score Risk**")
        if step2_done and latest_run:
            st.caption(f"Scored with {latest_run.model_selected.upper()}")
        else:
            st.caption("Analyze appointment attendance")

    with c3, st.container(border=True):
        s3_icon = "✅" if step3_done else "3️⃣"
        st.markdown(f"**{s3_icon} Review & Remind**")
        if step3_done:
            st.caption(f"{len(upcoming)} upcoming ranked")
        else:
            st.caption("Review risks and draft WhatsApp reminders")


# Backwards compatibility aliases
def render_risk_badge(risk_band: RiskBand, probability: float | None = None) -> None:
    status_badge(risk_band, probability)


def render_metric_card(
    title: str,
    value: str,
    subtext: str = "",
    delta: str | None = None,
) -> None:
    metric_card(label=title, value=value, help=subtext if subtext else None, delta=delta)


def render_privacy_banner() -> None:
    pass


def safe_page_link(
    page: str,
    label: str,
    icon: str | None = None,
    use_container_width: bool = True,
) -> None:
    """Safely render a page link or button fallback during standalone or isolated test execution."""
    try:
        st.page_link(page, label=label, icon=icon, use_container_width=use_container_width)
    except Exception:
        clean_target = page.rsplit("/", maxsplit=1)[-1].replace(".py", "")
        if st.button(label, use_container_width=use_container_width, key=f"safenav_{clean_target}_{label}"):
            with contextlib.suppress(Exception):
                st.switch_page(page)


def render_empty_state(title: str, description: str, icon: str = "📂") -> None:
    empty_state(icon=icon, title=title, message=description)
