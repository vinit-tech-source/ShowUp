"""Unit tests for synthetic dataset generator."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from showup.synthetic.generator import (
    export_synthetic_csv,
    generate_synthetic_dataset,
)


class TestSyntheticGenerator:
    """Verify synthetic dataset generator produces realistic, valid data."""

    def test_generate_synthetic_dataset_structure(self) -> None:
        df = generate_synthetic_dataset(n_clients=10, n_bookings=50, seed=123)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 50
        assert "client_id" in df.columns
        assert "client_name" in df.columns
        assert "appointment_datetime" in df.columns
        assert "service_type" in df.columns
        assert "outcome" in df.columns

        # Verify historical outcomes are attended or no_show
        hist = df[df["outcome"] != "pending"]
        assert len(hist) > 0
        assert set(hist["outcome"].unique()).issubset({"attended", "no_show"})

        # Verify upcoming outcomes are pending
        up = df[df["outcome"] == "pending"]
        assert len(up) > 0

    def test_reproducibility_with_seed(self) -> None:
        df1 = generate_synthetic_dataset(n_clients=5, n_bookings=20, seed=999)
        df2 = generate_synthetic_dataset(n_clients=5, n_bookings=20, seed=999)

        pd.testing.assert_frame_equal(df1, df2)

    def test_export_synthetic_csv_clean_and_messy(self, tmp_path: Path) -> None:
        df = generate_synthetic_dataset(n_clients=5, n_bookings=20, seed=42)

        clean_path = tmp_path / "clean.csv"
        export_synthetic_csv(df, clean_path, messy_headers=False)
        assert clean_path.exists()
        loaded_clean = pd.read_csv(clean_path)
        assert "client_id" in loaded_clean.columns

        messy_path = tmp_path / "messy.csv"
        export_synthetic_csv(df, messy_path, messy_headers=True)
        assert messy_path.exists()
        loaded_messy = pd.read_csv(messy_path)
        assert "Customer ID" in loaded_messy.columns
        assert "Booking Date & Time" in loaded_messy.columns
