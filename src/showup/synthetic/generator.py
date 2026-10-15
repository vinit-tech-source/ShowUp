"""Realistic synthetic dataset generator for appointment bookings.

Models domain-specific behavioral dynamics:
- Lead time penalty (longer lead time increases no-show probability).
- Upfront deposit protection (strongly reduces no-show probability).
- Confirmation reminder protection (reduces no-show probability).
- Repeat attendance habituation vs prior no-show recurrence.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SERVICES = [
    ("Physiotherapy Initial Consultation", 85.0),
    ("Physiotherapy Follow-Up", 65.0),
    ("Deep Tissue Massage", 75.0),
    ("Dry Needling Therapy", 70.0),
    ("Exercise Rehabilitation", 60.0),
]

CHANNELS = ["online", "phone", "walk-in", "referral"]

CLIENT_NAMES = [
    ("Sarah Jenkins", "+44 7700 900123", "en"),
    ("Rajesh Patel", "+91 98200 12345", "hi"),
    ("Priya Sharma", "+91 98201 54321", "hi"),
    ("Amit Deshmukh", "+91 98202 67890", "mr"),
    ("Sunita Kulkarni", "+91 98203 98765", "mr"),
    ("David Miller", "+1 555 234 5678", "en"),
    ("Elena Rostova", "+1 555 345 6789", "en"),
    ("Marcus Thorne", "+44 7700 900456", "en"),
    ("Neha Gupta", "+91 98204 11223", "hi"),
    ("Rohan Joshi", "+91 98205 33445", "mr"),
    ("Chloe Adams", "+1 555 456 7890", "en"),
    ("Liam O'Connor", "+44 7700 900789", "en"),
    ("Ananya Roy", "+91 98206 55667", "hi"),
    ("Vikram Shinde", "+91 98207 77889", "mr"),
    ("Hannah Abbott", "+1 555 567 8901", "en"),
]


@dataclass
class _ClientProfile:
    client_id: str
    name: str
    phone: str
    language: str
    reliability: float


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def _generate_historical_appointments(
    clients: list[_ClientProfile],
    n_historical: int,
    now: datetime,
    rng: random.Random,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    client_history_counts: dict[str, int] = {c.client_id: 0 for c in clients}
    client_no_show_counts: dict[str, int] = {c.client_id: 0 for c in clients}

    for _ in range(n_historical):
        client = rng.choice(clients)
        cid = client.client_id
        c_rel = client.reliability

        days_offset = rng.uniform(1.0, 120.0)
        app_dt = now - timedelta(days=days_offset)
        app_dt = app_dt.replace(hour=rng.randint(8, 17), minute=rng.choice([0, 15, 30, 45]))

        lead_time_days = rng.expovariate(1.0 / 7.0)
        lead_time_hours = min(1440.0, max(2.0, lead_time_days * 24.0))
        created_dt = app_dt - timedelta(hours=lead_time_hours)

        service_info = rng.choice(SERVICES)
        channel = rng.choices(CHANNELS, weights=[0.45, 0.30, 0.15, 0.10])[0]

        has_deposit = rng.random() < (0.35 if service_info[1] > 70.0 else 0.15)
        has_confirmed = rng.random() < 0.65

        z = -1.4
        z += (lead_time_hours / 24.0) * 0.04
        z -= 1.2 if has_deposit else 0.0
        z -= 0.7 if has_confirmed else 0.0
        z -= 0.6 * c_rel

        prior_ns = client_no_show_counts[cid]
        prior_vis = client_history_counts[cid]
        if prior_ns > 0:
            z += 0.8
        if prior_vis > 2:
            z -= 0.5

        if channel == "online":
            z += 0.4
        elif channel in ("walk-in", "referral"):
            z -= 0.5

        prob_no_show = _sigmoid(z)
        is_no_show = rng.random() < prob_no_show
        outcome = "no_show" if is_no_show else "attended"

        client_history_counts[cid] += 1
        if is_no_show:
            client_no_show_counts[cid] += 1

        rows.append(
            {
                "client_id": cid,
                "client_name": client.name,
                "phone": client.phone,
                "appointment_datetime": app_dt.strftime("%Y-%m-%d %H:%M"),
                "booking_created_at": created_dt.strftime("%Y-%m-%d %H:%M"),
                "service_type": service_info[0],
                "price": service_info[1],
                "channel": channel,
                "deposit_paid": has_deposit,
                "confirmed": has_confirmed,
                "outcome": outcome,
            }
        )
    return rows


def _generate_upcoming_appointments(
    clients: list[_ClientProfile],
    n_upcoming: int,
    now: datetime,
    rng: random.Random,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for _ in range(n_upcoming):
        client = rng.choice(clients)
        cid = client.client_id

        days_ahead = rng.uniform(0.5, 14.0)
        app_dt = now + timedelta(days=days_ahead)
        app_dt = app_dt.replace(hour=rng.randint(8, 17), minute=rng.choice([0, 15, 30, 45]))

        lead_time_days = rng.expovariate(1.0 / 6.0)
        lead_time_hours = max(2.0, lead_time_days * 24.0)
        created_dt = app_dt - timedelta(hours=lead_time_hours)

        service_info = rng.choice(SERVICES)
        channel = rng.choices(CHANNELS, weights=[0.50, 0.30, 0.10, 0.10])[0]
        has_deposit = rng.random() < 0.25
        has_confirmed = rng.random() < 0.40

        rows.append(
            {
                "client_id": cid,
                "client_name": client.name,
                "phone": client.phone,
                "appointment_datetime": app_dt.strftime("%Y-%m-%d %H:%M"),
                "booking_created_at": created_dt.strftime("%Y-%m-%d %H:%M"),
                "service_type": service_info[0],
                "price": service_info[1],
                "channel": channel,
                "deposit_paid": has_deposit,
                "confirmed": has_confirmed,
                "outcome": "pending",
            }
        )
    return rows


def generate_synthetic_dataset(
    n_clients: int = 40,
    n_bookings: int = 200,
    seed: int = 42,
    upcoming_ratio: float = 0.20,
) -> pd.DataFrame:
    """Generate a realistic synthetic bookings dataset with genuine behavioral correlations.

    Guarantees deterministic output given the seed.
    """
    rng = random.Random(seed)  # noqa: S311
    np_rng = np.random.default_rng(seed)

    # 1. Generate client profiles with latent reliability
    clients: list[_ClientProfile] = []
    for i in range(n_clients):
        template = CLIENT_NAMES[i % len(CLIENT_NAMES)]
        suffix = f" {i // len(CLIENT_NAMES) + 1}" if i >= len(CLIENT_NAMES) else ""
        c_id = f"client_{i + 1:03d}"
        latent_reliability = float(np_rng.normal(0.0, 1.0))
        clients.append(
            _ClientProfile(
                client_id=c_id,
                name=f"{template[0]}{suffix}",
                phone=template[1],
                language=template[2],
                reliability=latent_reliability,
            )
        )

    now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    n_upcoming = int(n_bookings * upcoming_ratio)
    n_historical = n_bookings - n_upcoming

    hist_rows = _generate_historical_appointments(clients, n_historical, now, rng)
    up_rows = _generate_upcoming_appointments(clients, n_upcoming, now, rng)

    df = pd.DataFrame(hist_rows + up_rows)
    return df.sort_values(by="appointment_datetime").reset_index(drop=True)


def export_synthetic_csv(
    df: pd.DataFrame,
    output_path: Path | str,
    *,
    messy_headers: bool = False,
) -> Path:
    """Save the synthetic dataset to CSV, optionally with messy third-party column names."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if messy_headers:
        col_map = {
            "client_id": "Customer ID",
            "client_name": "Full Name",
            "phone": "Mobile Number",
            "appointment_datetime": "Booking Date & Time",
            "booking_created_at": "Created On",
            "service_type": "Treatment",
            "price": "Fee Charged",
            "channel": "Source Platform",
            "deposit_paid": "Deposit Secured",
            "confirmed": "Is Confirmed",
            "outcome": "Attendance Status",
        }
        renamed_df = df.rename(columns=col_map)
        renamed_df.to_csv(out, index=False)
    else:
        df.to_csv(out, index=False)

    return out
