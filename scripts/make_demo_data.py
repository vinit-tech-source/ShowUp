"""CLI script to generate realistic synthetic appointment booking CSV datasets for ShowUp."""

from __future__ import annotations

import argparse
from pathlib import Path

from showup.synthetic.generator import export_synthetic_csv, generate_synthetic_dataset


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate realistic demo appointment data for ShowUp."
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default="data/demo_bookings.csv",
        help="Target output CSV file path (default: data/demo_bookings.csv).",
    )
    parser.add_argument(
        "--clients",
        "-c",
        type=int,
        default=50,
        help="Number of unique client profiles to simulate (default: 50).",
    )
    parser.add_argument(
        "--bookings",
        "-b",
        type=int,
        default=250,
        help="Total number of bookings (past + upcoming) to generate (default: 250).",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42).",
    )
    parser.add_argument(
        "--messy",
        action="store_true",
        help="Export with real-world third-party column headers to test automatic fuzzy mapping.",
    )

    args = parser.parse_args()

    print(
        f"Generating synthetic dataset: {args.bookings} bookings across {args.clients} clients..."
    )
    df = generate_synthetic_dataset(
        n_clients=args.clients,
        n_bookings=args.bookings,
        seed=args.seed,
    )

    out_path = Path(args.output)
    saved_file = export_synthetic_csv(df, out_path, messy_headers=args.messy)

    print(f"Successfully generated demo data at: {saved_file.resolve()}")
    print(f"Total rows: {len(df)}")
    print("Column headers:", list(df.columns))


if __name__ == "__main__":
    main()
