"""Data-grounded what-if analysis for deposits and confirmations."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Final

from showup.domain.enums import Outcome
from showup.domain.models import Booking

DEFAULT_MIN_SAMPLE_WHATIF: Final[int] = 20

CONFOUNDING_EXPLANATION: Final[str] = (
    "Important note on confounding: In observational business records, clients who pay upfront "
    "deposits or proactively confirm attendance may already possess higher intent or book "
    "higher-value services. This historical comparison reflects observed behavioral correlation, "
    "not an absolute causal guarantee."
)


@dataclass(frozen=True)
class StratifiedWhatIf:
    """Intervention comparison stratified by a specific service type."""

    service_name: str
    with_count: int
    with_show_rate: float
    without_count: int
    without_show_rate: float
    difference_pp: float
    is_visible: bool


@dataclass(frozen=True)
class GroundedWhatIfCard:
    """Factual what-if comparison card for an intervention."""

    intervention_key: str
    title: str
    with_count: int
    with_show_rate: float | None
    without_count: int
    without_show_rate: float | None
    difference_pp: float | None
    is_visible: bool
    factual_statement: str
    confounding_note: str
    min_sample_threshold: int
    stratified_breakdown: list[StratifiedWhatIf] = field(default_factory=list)


def _compute_group_show_rate(bookings: list[Booking]) -> tuple[int, float | None]:
    """Return (count, show_up_rate) for a collection of labeled bookings."""
    if not bookings:
        return 0, None
    total = len(bookings)
    attended = sum(1 for b in bookings if b.outcome == Outcome.ATTENDED)
    return total, round(float(attended) / float(total), 3)


def compute_grounded_whatif(
    bookings: list[Booking],
    *,
    min_sample: int = DEFAULT_MIN_SAMPLE_WHATIF,
) -> dict[str, GroundedWhatIfCard]:
    """Generate empirical show-up comparisons for deposits and confirmations.

    Enforces:
    - Purely observational, retrospective metrics.
    - Zero future prediction or fabricated claims.
    - Strict visibility gate: cards are hidden if sample size < min_sample.
    """
    labeled = [b for b in bookings if b.outcome in (Outcome.ATTENDED, Outcome.NO_SHOW)]

    # ── 1. Deposit Paid What-If ──────────────────────────────────────────
    with_deposit = [b for b in labeled if b.deposit_paid is True]
    without_deposit = [b for b in labeled if b.deposit_paid is False]

    n_with_dep, rate_with_dep = _compute_group_show_rate(with_deposit)
    n_wo_dep, rate_wo_dep = _compute_group_show_rate(without_deposit)

    dep_visible = (n_with_dep >= min_sample) and (n_wo_dep >= min_sample)

    if dep_visible and rate_with_dep is not None and rate_wo_dep is not None:
        diff_pp = round((rate_with_dep - rate_wo_dep) * 100.0, 1)
        dep_statement = (
            f"In your history, appointments with an upfront deposit had an observed "
            f"{rate_with_dep * 100:.1f}% show-up rate (N={n_with_dep}), compared to "
            f"{rate_wo_dep * 100:.1f}% for appointments without a deposit (N={n_wo_dep})."
        )
    else:
        diff_pp = None
        dep_statement = (
            f"Insufficient historical volume to compare deposits reliably "
            f"(with deposit N={n_with_dep}, without deposit N={n_wo_dep}; minimum required is "
            f"{min_sample} per group)."
        )

    # Service stratification for deposit
    deposit_stratified: list[StratifiedWhatIf] = []
    services_by_dep: dict[str, list[Booking]] = defaultdict(list)
    for b in labeled:
        if b.service_type:
            services_by_dep[b.service_type].append(b)

    for s_name, s_bookings in services_by_dep.items():
        s_with = [b for b in s_bookings if b.deposit_paid is True]
        s_wo = [b for b in s_bookings if b.deposit_paid is False]
        if len(s_with) >= min_sample and len(s_wo) >= min_sample:
            _, s_w_rate = _compute_group_show_rate(s_with)
            _, s_wo_rate = _compute_group_show_rate(s_wo)
            if s_w_rate is not None and s_wo_rate is not None:
                deposit_stratified.append(
                    StratifiedWhatIf(
                        service_name=s_name,
                        with_count=len(s_with),
                        with_show_rate=s_w_rate,
                        without_count=len(s_wo),
                        without_show_rate=s_wo_rate,
                        difference_pp=round((s_w_rate - s_wo_rate) * 100.0, 1),
                        is_visible=True,
                    )
                )

    deposit_card = GroundedWhatIfCard(
        intervention_key="deposit_paid",
        title="Upfront Deposits",
        with_count=n_with_dep,
        with_show_rate=rate_with_dep,
        without_count=n_wo_dep,
        without_show_rate=rate_wo_dep,
        difference_pp=diff_pp,
        is_visible=dep_visible,
        factual_statement=dep_statement,
        confounding_note=CONFOUNDING_EXPLANATION,
        min_sample_threshold=min_sample,
        stratified_breakdown=deposit_stratified,
    )

    # ── 2. Confirmation Received What-If ─────────────────────────────────
    with_conf = [b for b in labeled if b.confirmed is True]
    without_conf = [b for b in labeled if b.confirmed is False]

    n_with_conf, rate_with_conf = _compute_group_show_rate(with_conf)
    n_wo_conf, rate_wo_conf = _compute_group_show_rate(without_conf)

    conf_visible = (n_with_conf >= min_sample) and (n_wo_conf >= min_sample)

    if conf_visible and rate_with_conf is not None and rate_wo_conf is not None:
        conf_diff = round((rate_with_conf - rate_wo_conf) * 100.0, 1)
        conf_statement = (
            f"In your history, appointments confirmed by the client had an observed "
            f"{rate_with_conf * 100:.1f}% show-up rate (N={n_with_conf}), compared to "
            f"{rate_wo_conf * 100:.1f}% for unconfirmed appointments (N={n_wo_conf})."
        )
    else:
        conf_diff = None
        conf_statement = (
            f"Insufficient historical volume to compare confirmations reliably "
            f"(confirmed N={n_with_conf}, unconfirmed N={n_wo_conf}; minimum required is "
            f"{min_sample} per group)."
        )

    confirmation_card = GroundedWhatIfCard(
        intervention_key="confirmed",
        title="Prior Confirmation",
        with_count=n_with_conf,
        with_show_rate=rate_with_conf,
        without_count=n_wo_conf,
        without_show_rate=rate_wo_conf,
        difference_pp=conf_diff,
        is_visible=conf_visible,
        factual_statement=conf_statement,
        confounding_note=CONFOUNDING_EXPLANATION,
        min_sample_threshold=min_sample,
        stratified_breakdown=[],
    )

    return {
        "deposit_paid": deposit_card,
        "confirmed": confirmation_card,
    }
