"""Data loader for the Settlement Intelligence Agent.

Reads gateway.csv, bank.csv, and ledger.csv once at startup, validates column
contracts, parses timestamps, normalizes statuses, and returns DataFrames
indexed by transaction_id while keeping transaction_id as a regular column.
"""

from __future__ import annotations

import logging
import os

import pandas as pd

from config import (
    BANK_REQUIRED_COLUMNS,
    DATA_DIR,
    GATEWAY_REQUIRED_COLUMNS,
    LEDGER_REQUIRED_COLUMNS,
    VALID_BANK_STATUSES,
    VALID_GATEWAY_STATUSES,
    VALID_LEDGER_STATUSES,
)


logger = logging.getLogger(__name__)


def _validate_columns(df: pd.DataFrame, required: list[str], filename: str) -> None:
    missing = set(required) - set(df.columns)
    if missing:
        raise ValueError(f"{filename} is missing required columns: {sorted(missing)}")


def _normalize_status(
    series: pd.Series,
    valid_values: set[str],
    column_name: str,
) -> pd.Series:
    cleaned = series.astype(str).str.strip().str.upper()
    invalid_mask = ~cleaned.isin(valid_values)
    invalid_count = int(invalid_mask.sum())
    if invalid_count:
        samples = cleaned[invalid_mask].unique()[:5]
        logger.warning(
            "%s contains %d rows with unexpected values: %s",
            column_name,
            invalid_count,
            samples,
        )
    return cleaned


def _parse_datetime_column(df: pd.DataFrame, column: str, filename: str) -> None:
    df[column] = pd.to_datetime(df[column], format="mixed", errors="coerce")
    nat_count = int(df[column].isna().sum())
    if nat_count:
        logger.warning("%s: %d unparseable values in '%s'.", filename, nat_count, column)


def _check_duplicates(df: pd.DataFrame, filename: str) -> None:
    duplicate_count = int(df["transaction_id"].duplicated().sum())
    if duplicate_count:
        logger.warning(
            "%s contains %d duplicate transaction_id entries.",
            filename,
            duplicate_count,
        )


def _check_empty_transaction_ids(df: pd.DataFrame, filename: str) -> None:
    empty_count = int(
        df["transaction_id"].isna().sum()
        + df["transaction_id"].astype(str).str.strip().eq("").sum()
    )
    if empty_count:
        logger.warning("%s contains %d empty transaction_id values.", filename, empty_count)


def _check_negative_amounts(df: pd.DataFrame, column: str, filename: str) -> None:
    if column not in df.columns:
        return
    numeric = pd.to_numeric(df[column], errors="coerce")
    negative_count = int(numeric.lt(0).sum())
    if negative_count:
        logger.warning(
            "%s contains %d negative values in '%s'.",
            filename,
            negative_count,
            column,
        )


def _read_csv(data_dir: str, filename: str) -> pd.DataFrame:
    filepath = os.path.join(data_dir, filename)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"{filename} not found at {filepath}")
    return pd.read_csv(filepath)


def load_gateway(data_dir: str) -> pd.DataFrame:
    df = _read_csv(data_dir, "gateway.csv")
    _validate_columns(df, GATEWAY_REQUIRED_COLUMNS, "gateway.csv")

    _parse_datetime_column(df, "gateway_timestamp", "gateway.csv")
    df["gateway_status"] = _normalize_status(
        df["gateway_status"], VALID_GATEWAY_STATUSES, "gateway_status"
    )

    _check_empty_transaction_ids(df, "gateway.csv")
    _check_duplicates(df, "gateway.csv")
    _check_negative_amounts(df, "amount", "gateway.csv")
    return df


def load_bank(data_dir: str) -> pd.DataFrame:
    df = _read_csv(data_dir, "bank.csv")
    _validate_columns(df, BANK_REQUIRED_COLUMNS, "bank.csv")

    _parse_datetime_column(df, "bank_received_at", "bank.csv")
    _parse_datetime_column(df, "bank_updated_at", "bank.csv")
    df["bank_status"] = _normalize_status(
        df["bank_status"], VALID_BANK_STATUSES, "bank_status"
    )

    _check_empty_transaction_ids(df, "bank.csv")
    _check_duplicates(df, "bank.csv")
    _check_negative_amounts(df, "settlement_amount", "bank.csv")
    return df


def load_ledger(data_dir: str) -> pd.DataFrame:
    df = _read_csv(data_dir, "ledger.csv")
    _validate_columns(df, LEDGER_REQUIRED_COLUMNS, "ledger.csv")

    _parse_datetime_column(df, "ledger_timestamp", "ledger.csv")
    df["ledger_status"] = _normalize_status(
        df["ledger_status"], VALID_LEDGER_STATUSES, "ledger_status"
    )

    _check_empty_transaction_ids(df, "ledger.csv")
    _check_duplicates(df, "ledger.csv")
    _check_negative_amounts(df, "ledger_amount", "ledger.csv")
    return df


def load_data(data_dir: str = DATA_DIR) -> dict[str, pd.DataFrame]:
    """Load and prepare Gateway, Bank, and Ledger DataFrames."""
    gateway_df = load_gateway(data_dir)
    bank_df = load_bank(data_dir)
    ledger_df = load_ledger(data_dir)

    merged = gateway_df.merge(bank_df, on="transaction_id", how="inner")
    bad_order = merged["bank_received_at"] < merged["gateway_timestamp"]
    bad_order_count = int(bad_order.sum())
    if bad_order_count:
        logger.warning(
            "%d transactions have bank_received_at earlier than gateway_timestamp.",
            bad_order_count,
        )

    gateway_df = gateway_df.set_index("transaction_id", drop=False)
    bank_df = bank_df.set_index("transaction_id", drop=False)
    ledger_df = ledger_df.set_index("transaction_id", drop=False)

    logger.info(
        "Loaded dataset: Gateway (%d rows), Bank (%d rows), Ledger (%d rows)",
        len(gateway_df),
        len(bank_df),
        len(ledger_df),
    )

    return {
        "gateway": gateway_df,
        "bank": bank_df,
        "ledger": ledger_df,
    }
