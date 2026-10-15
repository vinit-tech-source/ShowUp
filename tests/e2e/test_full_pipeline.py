"""End-to-end integration and offline verification test for the full ShowUp pipeline."""

from __future__ import annotations

import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine

from showup.domain.enums import RiskBand
from showup.ingest.dedupe import dedupe_bookings
from showup.ingest.mapper import apply_mapping, suggest_mappings
from showup.ingest.reader import read_csv_safe
from showup.ingest.validator import validate_and_transform_df
from showup.insights.cost_report import compute_cost_report
from showup.insights.whatif import compute_grounded_whatif
from showup.jobs.worker import execute_scoring_job, get_scored_upcoming_ranked
from showup.messaging.guardrails import draft_message_with_guardrails
from showup.messaging.ollama_client import OllamaClient
from showup.messaging.whatsapp import build_wa_link
from showup.storage.database import get_session_factory, init_db
from showup.storage.repositories import BookingRepo, ClientRepo, wipe_all
from showup.synthetic.generator import export_synthetic_csv, generate_synthetic_dataset


class TestFullPipelineE2E:
    """Complete end-to-end verification of ShowUp from CSV ingest to WhatsApp drafting."""

    def test_full_lifecycle(self, tmp_path: Path) -> None:
        # ── 1. Generate realistic synthetic data ──────────────────────
        df_raw = generate_synthetic_dataset(
            n_clients=35,
            n_bookings=160,
            seed=42,
            upcoming_ratio=0.25,
        )
        csv_file = tmp_path / "incoming_appointments.csv"
        export_synthetic_csv(df_raw, csv_file, messy_headers=True)
        assert csv_file.exists()

        # ── 2. Ingest: Sniff encoding & delimiter ─────────────────────
        content_bytes = csv_file.read_bytes()
        df_loaded, enc, _delim = read_csv_safe(content_bytes)
        assert len(df_loaded) == 160
        assert enc.lower() in ("utf-8", "ascii")

        # ── 3. Mapping: Auto-suggest columns on messy headers ─────────
        headers = list(df_loaded.columns)
        suggestions = suggest_mappings(headers)
        assert "client_id" in suggestions
        assert "appointment_datetime" in suggestions

        mapped_df = apply_mapping(df_loaded, suggestions)
        assert "client_id" in mapped_df.columns
        assert "appointment_datetime" in mapped_df.columns

        # ── 4. Validation & Deduplication ─────────────────────────────
        clients, bookings, val_report = validate_and_transform_df(
            mapped_df, source_file="incoming_appointments.csv"
        )
        assert len(bookings) > 0
        assert val_report.error_rows == 0

        deduped_bookings, _ = dedupe_bookings(bookings)
        assert len(deduped_bookings) == len(bookings)

        # ── 5. Storage: Setup isolated SQLite database ────────────────
        db_path = tmp_path / "showup_e2e.db"
        engine = create_engine(f"sqlite:///{db_path}")
        init_db(engine, db_path)
        session_factory = get_session_factory(engine)

        with session_factory() as session:
            for c in clients:
                ClientRepo.get_or_create(
                    session,
                    external_id=c.external_id,
                    name=c.name,
                    phone=c.phone,
                    language=c.language,
                    client_id=c.id,
                )
            BookingRepo.add_batch(session, deduped_bookings)
            session.commit()

            labeled = BookingRepo.list_labeled(session)
            upcoming = BookingRepo.list_upcoming(session)
            assert len(labeled) > 0
            assert len(upcoming) > 0

        # ── 6. Background Worker: Execute full scoring job ────────────
        run = execute_scoring_job(session_factory=session_factory)
        assert run.status.value == "completed"
        assert run.tier in (1, 2)
        assert run.model_selected in ("rules", "logistic", "tabpfn")

        # ── 7. Scored Bookings Ranking ────────────────────────────────
        with session_factory() as session:
            scored_ranked = get_scored_upcoming_ranked(session)
            assert len(scored_ranked) == len(upcoming)

            # Ensure high risk precedes medium and low
            seen_bands = [res.risk_band for _, res, _ in scored_ranked if res]
            assert RiskBand.HIGH in seen_bands or RiskBand.MEDIUM in seen_bands

            first_booking, first_result, first_client = scored_ranked[0]
            assert first_result is not None
            assert 0.0 <= first_result.probability <= 1.0
            assert len(first_result.explanation) > 0

        # ── 8. Cost Report Insights ───────────────────────────────────
        with session_factory() as session:
            cost_rep = compute_cost_report(labeled)
            assert cost_rep.total_labeled == len(labeled)
            assert cost_rep.overall_no_show_rate is not None
            assert 0.0 <= cost_rep.overall_no_show_rate <= 1.0
            assert cost_rep.total_lost_revenue > 0

        # ── 9. What-If Insights ───────────────────────────────────────
        with session_factory() as session:
            whatif_cards = compute_grounded_whatif(labeled)
            assert "deposit_paid" in whatif_cards
            assert "confirmed" in whatif_cards

        # ── 10. Messaging: Draft with Mock Ollama & Guardrails ────────
        ollama_client = OllamaClient()
        fake_response = (
            f"Hi {first_client.name}, confirming your appointment on "
            f"{first_booking.appointment_at.strftime('%b %d')}. Looking forward to seeing you!"
        )
        with patch("httpx.Client.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"response": fake_response}
            mock_post.return_value = mock_resp

            draft, is_llm, _violations = draft_message_with_guardrails(
                ollama_client=ollama_client,
                client_name=first_client.name,
                service_name=first_booking.service_type or "Appointment",
                appointment_time_str=first_booking.appointment_at.strftime("%b %d"),
                language_code="en",
                risk_band=first_result.risk_band,
            )
            assert is_llm is True
            assert len(draft.split()) <= 40
            assert first_client.name in draft

            # WhatsApp wa.me link
            wa_link = build_wa_link(first_client.phone or "", draft)
            assert "https://wa.me/" in wa_link
            assert "text=" in wa_link

        # ── 11. Privacy: Clean Wipe All ───────────────────────────────
        with session_factory() as session:
            wipe_all(data_dir=tmp_path, session=session)
            assert len(ClientRepo.list_all(session)) == 0
            assert len(BookingRepo.list_all(session)) == 0

    def test_zero_outbound_network_calls(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Assert that no non-localhost socket connections are attempted during execution."""
        original_connect = socket.socket.connect

        def guarded_connect(self: socket.socket, address: tuple[str, int] | str) -> None:
            host = address[0] if isinstance(address, tuple) else address
            # Strictly allow localhost / 127.0.0.1 / ::1
            if host not in ("127.0.0.1", "localhost", "::1"):
                raise AssertionError(
                    f"CRITICAL PRIVACY VIOLATION: ShowUp attempted outbound connection to {host}!"
                )
            original_connect(self, address)

        monkeypatch.setattr(socket.socket, "connect", guarded_connect)

        # Generate data and score
        df = generate_synthetic_dataset(n_clients=20, n_bookings=60, seed=123)
        assert len(df) == 60
