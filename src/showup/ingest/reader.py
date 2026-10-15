"""Safe CSV reader with automatic encoding and delimiter sniffing."""

from __future__ import annotations

import csv
import io
from pathlib import Path

import chardet
import pandas as pd

from showup.logging_setup import get_logger

logger = get_logger(__name__)

DEFAULT_DELIMITERS = [",", ";", "\t", "|"]


class CsvReadError(Exception):
    """Raised when CSV reading fails."""


def detect_encoding(raw_bytes: bytes) -> str:
    """Detect text encoding using chardet on the first 64KB.

    Falls back to 'utf-8' if confidence is low or detection fails.
    """
    sample = raw_bytes[:65536]
    result = chardet.detect(sample)
    encoding = result.get("encoding")
    confidence = result.get("confidence", 0.0)

    if not encoding or confidence < 0.5:
        return "utf-8"

    # Normalize common Windows encodings
    normalized = encoding.lower().strip()
    if normalized in ("ascii", "utf-8-sig"):
        return "utf-8"
    if normalized in ("windows-1252", "iso-8859-1", "latin1"):
        return "latin1"

    return encoding


def detect_delimiter(sample_text: str) -> str:
    """Sniff the CSV delimiter from a text sample.

    Falls back to comma if sniffing is inconclusive.
    """
    if not sample_text.strip():
        return ","

    lines = [line for line in sample_text.splitlines() if line.strip()][:10]
    sample = "\n".join(lines)

    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=",".join(DEFAULT_DELIMITERS))
        return dialect.delimiter
    except csv.Error:
        # Fallback heuristic: count delimiter occurrences in first non-empty line
        first_line = lines[0] if lines else ""
        best_delim = ","
        best_count = 0
        for delim in DEFAULT_DELIMITERS:
            count = first_line.count(delim)
            if count > best_count:
                best_count = count
                best_delim = delim
        return best_delim


def read_csv_safe(
    source: bytes | str | Path,
    *,
    max_bytes: int = 50 * 1024 * 1024,
) -> tuple[pd.DataFrame, str, str]:
    """Safely read CSV data into a pandas DataFrame.

    Detects encoding and delimiter, respects size limits, and returns
    (dataframe, detected_encoding, detected_delimiter).

    Raises:
        CsvReadError: if file exceeds size limit, is empty, or cannot be parsed.
    """
    # 1. Obtain bytes
    if isinstance(source, Path):
        if not source.exists():
            raise CsvReadError(f"File not found: {source}")
        file_size = source.stat().st_size
        if file_size > max_bytes:
            raise CsvReadError(
                f"File size ({file_size / (1024 * 1024):.1f}MB) exceeds limit of "
                f"{max_bytes / (1024 * 1024):.0f}MB."
            )
        raw_bytes = source.read_bytes()
    elif isinstance(source, str):
        raw_bytes = source.encode("utf-8")
    else:
        raw_bytes = source

    if len(raw_bytes) > max_bytes:
        raise CsvReadError(
            f"Upload size ({len(raw_bytes) / (1024 * 1024):.1f}MB) exceeds limit of "
            f"{max_bytes / (1024 * 1024):.0f}MB."
        )

    if not raw_bytes.strip():
        raise CsvReadError("The provided CSV file is empty.")

    # 2. Detect encoding
    encoding = detect_encoding(raw_bytes)

    # 3. Decode sample for delimiter sniffing
    try:
        text_content = raw_bytes.decode(encoding, errors="replace")
    except Exception as e:
        logger.warning("encoding_decode_failed", encoding=encoding, error=str(e))
        text_content = raw_bytes.decode("utf-8", errors="replace")
        encoding = "utf-8"

    delimiter = detect_delimiter(text_content[:8192])

    # 4. Parse into DataFrame with pandas
    try:
        df = pd.read_csv(
            io.StringIO(text_content),
            sep=delimiter,
            dtype=str,  # read all as string initially to avoid corrupting client IDs / phones
            skipinitialspace=True,
            on_bad_lines="skip",
        )
    except Exception as e:
        raise CsvReadError(f"Failed to parse CSV: {e}") from e

    if df.empty or len(df.columns) == 0:
        raise CsvReadError("The CSV contains no tabular data or columns.")

    # Clean whitespace in column names
    df.columns = df.columns.str.strip()

    logger.info(
        "csv_read_success",
        rows=len(df),
        columns=len(df.columns),
        encoding=encoding,
        delimiter=delimiter,
    )
    return df, encoding, delimiter
