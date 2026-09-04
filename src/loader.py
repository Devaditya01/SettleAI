"""
Data loader for the Settlement Intelligence Agent.

Reads gateway.csv, bank.csv, and ledger.csv once at startup,
parses timestamps, normalizes statuses, validates column
contracts, and returns clean DataFrames indexed by transaction_id.

No other module should read CSVs directly.
"""

import logging
import os

import pandas as pd

from config import (
    DATA_DIR,
    GATEWAY_REQUIRED_COLUMNS,
    BANK_REQUIRED_COLUMNS,
    LEDGER_REQUIRED_COLUMNS,
    VALID_GATEWAY_STATUSES,
    VALID_BANK_STATUSES,
    VALID_LEDGER_STATUSES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_columns(df: pd.DataFrame, required: list[str], filename: str) -> None:
    """Raise ValueError if any required column is missing."""
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(
            f"{filename} is missing required columns: {sorted(missing)}"
        )


def _normalize_status(series: pd.Series, valid_values: set, column_name: str) -> pd.Series:
    """Uppercase, strip whitespace, and warn on unexpected values."""
    cleaned = series.astype(str).str.strip().str.upper()
    invalid_mask = ~cleaned.isin(valid_values)
    n_invalid = invalid_mask.sum()
    if n_invalid > 0:
        samples = cleaned[invalid_mask].unique()[:5]
        logger.warning(
            "%s contains %d rows with unexpected values: %s",
            column_name, n_invalid, samples
        )
    return cleaned


def _check_duplicates(df: pd.DataFrame, filename: str) -> None:
    """Warn if transaction_id has duplicates within a single file."""
    dupes = df["transaction_id"].duplicated()
    n_dupes = dupes.sum()
    if n_dupes > 0:
        logger.warning(
            "%s contains %d duplicate transaction_id entries.", filename, n_dupes
        )


def _check_negative_amounts(df: pd.DataFrame, column: str, filename: str) -> None:
    """Warn if any monetary amount is negative."""
    if column not in df.columns:
        return
    negatives = (df[column] < 0).sum()
    if negatives > 0:
        logger.warning(
            "%s contains %d negative values in '%s'.", filename, negatives, column
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_gateway(data_dir: str) -> pd.DataFrame:
    """Load and clean gateway.csv."""
    filepath = os.path.join(data_dir, "gateway.csv")
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Gateway data not found: {filepath}")

    df = pd.read_csv(filepath)
    _validate_columns(df, GATEWAY_REQUIRED_COLUMNS, "gateway.csv")

    # Parse timestamps (gateway has no microseconds)
    df["gateway_timestamp"] = pd.to_datetime(
        df["gateway_timestamp"], format="mixed", errors="coerce"
    )
    nat_count = df["gateway_timestamp"].isna().sum()
    if nat_count > 0:
        logger.warning("gateway.csv: %d unparseable timestamps coerced to NaT.", nat_count)

    # Normalize statuses
    df["gateway_status"] = _normalize_status(
        df["gateway_status"], VALID_GATEWAY_STATUSES, "gateway_status"
    )

    # Data quality
    _check_duplicates(df, "gateway.csv")
    _check_negative_amounts(df, "amount", "gateway.csv")

    return df


def load_bank(data_dir: str) -> pd.DataFrame:
    """Load and clean bank.csv."""
    filepath = os.path.join(data_dir, "bank.csv")
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Bank data not found: {filepath}")

    df = pd.read_csv(filepath)
    _validate_columns(df, BANK_REQUIRED_COLUMNS, "bank.csv")

    # Parse timestamps (bank has microseconds)
    for col in ("bank_received_at", "bank_updated_at"):
        df[col] = pd.to_datetime(df[col], format="mixed", errors="coerce")
        nat_count = df[col].isna().sum()
        if nat_count > 0:
            logger.warning("bank.csv: %d unparseable values in '%s'.", nat_count, col)

    # Normalize statuses
    df["bank_status"] = _normalize_status(
        df["bank_status"], VALID_BANK_STATUSES, "bank_status"
    )

    # Data quality
    _check_duplicates(df, "bank.csv")
    _check_negative_amounts(df, "settlement_amount", "bank.csv")

    return df


def load_ledger(data_dir: str) -> pd.DataFrame:
    """Load and clean ledger.csv."""
    filepath = os.path.join(data_dir, "ledger.csv")
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Ledger data not found: {filepath}")

    df = pd.read_csv(filepath)
    _validate_columns(df, LEDGER_REQUIRED_COLUMNS, "ledger.csv")

    # Parse timestamps (ledger has microseconds)
    df["ledger_timestamp"] = pd.to_datetime(
        df["ledger_timestamp"], format="mixed", errors="coerce"
    )
    nat_count = df["ledger_timestamp"].isna().sum()
    if nat_count > 0:
        logger.warning("ledger.csv: %d unparseable timestamps coerced to NaT.", nat_count)

    # Normalize statuses
    df["ledger_status"] = _normalize_status(
        df["ledger_status"], VALID_LEDGER_STATUSES, "ledger_status"
    )

    # Data quality
    _check_duplicates(df, "ledger.csv")
    _check_negative_amounts(df, "ledger_amount", "ledger.csv")

    return df


def load_data(data_dir: str = DATA_DIR) -> dict:
    """Load all three settlement data sources.

    Call this once at application startup. The returned DataFrames
    are indexed by transaction_id for O(1) lookups by the tracer.

    Args:
        data_dir: Path to the directory containing the CSV files.

    Returns:
        dict with keys "gateway", "bank", "ledger", each holding
        a cleaned pandas DataFrame indexed by transaction_id.
    """
    gateway_df = load_gateway(data_dir)
    bank_df = load_bank(data_dir)
    ledger_df = load_ledger(data_dir)

    # Cross-file timestamp sanity check:
    # bank_received_at should not precede gateway_timestamp for the same txn.
    merged = gateway_df.merge(bank_df, on="transaction_id", how="inner")
    bad_order = merged["bank_received_at"] < merged["gateway_timestamp"]
    n_bad = bad_order.sum()
    if n_bad > 0:
        logger.warning(
            "%d transactions have bank_received_at earlier than gateway_timestamp "
            "(impossible timestamp order).", n_bad
        )

    # Index by transaction_id for fast downstream lookups.
    gateway_df = gateway_df.set_index("transaction_id")
    bank_df = bank_df.set_index("transaction_id")
    ledger_df = ledger_df.set_index("transaction_id")

    logger.info(
        "Data loaded — gateway: %d, bank: %d, ledger: %d rows.",
        len(gateway_df), len(bank_df), len(ledger_df)
    )

    return {
        "gateway": gateway_df,
        "bank": bank_df,
        "ledger": ledger_df,
    }
