"""Background scoring worker executing model training, backtesting, and booking scoring."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from showup.domain.enums import Outcome, RiskBand, RunStatus
from showup.domain.models import Booking, Client, ScoringResult, ScoringRun
from showup.features.builder import build_features_matrix
from showup.logging_setup import get_logger
from showup.scoring.backtest import run_time_ordered_backtest
from showup.scoring.baseline import LogisticBaseline
from showup.scoring.rules import score_features_row_with_rules
from showup.scoring.selector import select_scoring_model
from showup.scoring.tabpfn_scorer import TabPFNScorer
from showup.storage.database import get_session
from showup.storage.repositories import BookingRepo, ScoringRepo

logger = get_logger(__name__)


def _score_batch(
    upcoming: list[Booking],
    history: list[Booking],
    model_name: str,
    X_upcoming: pd.DataFrame,
) -> tuple[list[ScoringResult], str]:
    """Score upcoming bookings using the designated model."""
    scoring_results: list[ScoringResult] = []
    effective_model = model_name

    if effective_model == "tabpfn":
        tabpfn_scorer = TabPFNScorer()
        if tabpfn_scorer.is_available:
            X_hist = build_features_matrix(history, history)
            y_hist = np.array([1 if b.outcome == Outcome.NO_SHOW else 0 for b in history])
            probas = tabpfn_scorer.fit_predict_proba(X_hist, y_hist, X_upcoming)
            for i, booking in enumerate(upcoming):
                p = float(probas[i])
                band = tabpfn_scorer.classify_risk_band(p)
                expl = (
                    f"{band.value.capitalize()} risk ({p * 100:.0f}% chance): "
                    f"predicted by TabPFN v2 foundation model."
                )
                scoring_results.append(
                    ScoringResult(
                        booking_id=booking.id,
                        risk_band=band,
                        probability=p,
                        model_used="tabpfn",
                        scored_at=datetime.now(UTC),
                        explanation=expl,
                    )
                )
            return scoring_results, "tabpfn"
        effective_model = "logistic"

    if effective_model == "logistic":
        X_hist = build_features_matrix(history, history)
        y_hist = np.array([1 if b.outcome == Outcome.NO_SHOW else 0 for b in history])
        baseline = LogisticBaseline().fit(X_hist, y_hist)
        probas = baseline.predict_proba(X_upcoming)

        for i, booking in enumerate(upcoming):
            p = float(probas[i])
            band = baseline.classify_risk_band(p)
            row_feat = X_upcoming.iloc[i] if not X_upcoming.empty else {}
            expl = baseline.explain_prediction(row_feat, p)
            scoring_results.append(
                ScoringResult(
                    booking_id=booking.id,
                    risk_band=band,
                    probability=p,
                    model_used="logistic",
                    scored_at=datetime.now(UTC),
                    explanation=expl,
                )
            )
        return scoring_results, "logistic"

    # Fallback to heuristic rules
    for i, booking in enumerate(upcoming):
        row_feat = X_upcoming.iloc[i] if not X_upcoming.empty else {}
        band, p, expl = score_features_row_with_rules(row_feat)
        scoring_results.append(
            ScoringResult(
                booking_id=booking.id,
                risk_band=band,
                probability=p,
                model_used="rules",
                scored_at=datetime.now(UTC),
                explanation=expl,
            )
        )
    return scoring_results, "rules"


def execute_scoring_job(
    session_factory: Callable[[], Session] | None = None,
    run_id: UUID | None = None,
) -> ScoringRun:
    """Execute complete scoring workflow: data fetch, model selection, and inference."""
    get_sess = session_factory or get_session
    job_id = run_id or uuid4()

    with get_sess() as session:
        initial_run = ScoringRun(
            id=job_id,
            started_at=datetime.now(UTC),
            status=RunStatus.RUNNING,
            tier=1,
            model_selected="pending",
            progress_pct=5,
        )
        ScoringRepo.create_scoring_run(session, initial_run)
        session.commit()

    try:
        with get_sess() as session:
            all_bookings = BookingRepo.list_all(session)
            now = datetime.now(UTC)

            history = sorted(
                [
                    b
                    for b in all_bookings
                    if b.outcome in (Outcome.ATTENDED, Outcome.NO_SHOW) and b.appointment_at < now
                ],
                key=lambda b: b.appointment_at,
            )
            upcoming = sorted(
                [
                    b
                    for b in all_bookings
                    if b.outcome in (Outcome.PENDING, None) or b.appointment_at >= now
                ],
                key=lambda b: b.appointment_at,
            )

            ScoringRepo.update_scoring_run_progress(session, job_id, 20)
            session.commit()

            if not upcoming:
                ScoringRepo.complete_scoring_run(
                    session,
                    job_id,
                    tier=1,
                    model_selected="none",
                    metrics={"upcoming_count": 0},
                    explanation="No upcoming bookings found to score.",
                )
                session.commit()
                latest = ScoringRepo.get_latest_scoring_run(session)
                return latest or initial_run

            total_labeled = len(history)
            total_no_shows = sum(1 for b in history if b.outcome == Outcome.NO_SHOW)

            ScoringRepo.update_scoring_run_progress(session, job_id, 40)
            session.commit()

            if total_labeled >= 30 and total_no_shows >= 5:
                backtest_summary = run_time_ordered_backtest(
                    history,
                    min_train_size=max(20, total_labeled // 3),
                    step_size=max(5, total_labeled // 10),
                    random_state=42,
                )
                selection = select_scoring_model(
                    total_labeled=total_labeled,
                    total_no_shows=total_no_shows,
                    backtest=backtest_summary,
                )
            else:
                selection = select_scoring_model(
                    total_labeled=total_labeled,
                    total_no_shows=total_no_shows,
                )

            tier = selection.tier
            model_name = selection.selected_model
            explanation = selection.explanation
            metrics_dict = selection.metrics

            ScoringRepo.update_scoring_run_progress(session, job_id, 65)
            session.commit()

            # Predict and score
            X_upcoming = build_features_matrix(upcoming, history)
            scoring_results, final_model = _score_batch(upcoming, history, model_name, X_upcoming)
            model_name = final_model

            ScoringRepo.update_scoring_run_progress(session, job_id, 85)
            session.commit()

            ScoringRepo.save_scoring_results(session, scoring_results)
            ScoringRepo.complete_scoring_run(
                session,
                job_id,
                tier=tier,
                model_selected=model_name,
                metrics=metrics_dict,
                explanation=explanation,
            )
            session.commit()

            latest = ScoringRepo.get_latest_scoring_run(session)
            logger.info(
                "scoring_job_completed",
                run_id=str(job_id),
                tier=tier,
                model=model_name,
                scored_count=len(scoring_results),
            )
            return latest or initial_run

    except Exception as e:
        logger.error("scoring_job_failed", run_id=str(job_id), error=str(e))
        with get_sess() as session:
            ScoringRepo.fail_scoring_run(session, job_id, str(e))
            session.commit()
        raise


def start_background_scoring(
    session_factory: Callable[[], Session] | None = None,
) -> UUID:
    """Trigger background scoring worker thread. Returns run_id."""
    get_sess = session_factory or get_session
    job_id = uuid4()

    thread = threading.Thread(
        target=execute_scoring_job,
        kwargs={"session_factory": get_sess, "run_id": job_id},
        daemon=True,
    )
    thread.start()
    return job_id


def is_scoring_in_progress(session: Session) -> bool:
    """Check if any scoring job is actively running."""
    latest = ScoringRepo.get_latest_scoring_run(session)
    if latest and latest.status == RunStatus.RUNNING:
        # Check if started within last 10 minutes to guard against dead threads
        age_sec = (datetime.now(UTC) - latest.started_at).total_seconds()
        return age_sec < 600.0
    return False


def get_scored_upcoming_ranked(
    session: Session,
) -> list[tuple[Booking, ScoringResult | None, Client]]:
    """Fetch upcoming bookings ranked with high risk first, then medium, then low."""
    rows = ScoringRepo.list_scored_upcoming(session)

    band_priority = {
        RiskBand.HIGH: 0,
        RiskBand.MEDIUM: 1,
        RiskBand.LOW: 2,
        None: 3,
    }

    def sort_key(item: tuple[Booking, ScoringResult | None, Client]) -> tuple[int, float, datetime]:
        _, result, _ = item
        band = result.risk_band if result else None
        priority = band_priority.get(band, 3)
        prob = -result.probability if result and result.probability is not None else 0.0
        app_at = item[0].appointment_at
        return (priority, prob, app_at)

    return sorted(rows, key=sort_key)
