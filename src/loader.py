"""
Data loader for the Settlement Intelligence Agent.

Loads gateway.csv, bank.csv, and ledger.csv from a data directory,
parses ISO/UTC timestamp columns into pd.Timestamp objects, normalizes string columns,
and sets transaction_id as the DataFrame index for O(1) lookups.
"""

import os
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def load_data(data_dir: str = "data") -> dict[str, pd.DataFrame]:
    """Load and prepare Gateway, Bank, and Ledger DataFrames.

    Args:
        data_dir: Path to directory containing gateway.csv, bank.csv, ledger.csv.

    Returns:
        Dict with keys 'gateway', 'bank', 'ledger', mapping to indexed DataFrames.
    """
    gw_path = os.path.join(data_dir, "gateway.csv")
    bank_path = os.path.join(data_dir, "bank.csv")
    ledger_path = os.path.join(data_dir, "ledger.csv")

    if not os.path.exists(gw_path):
        raise FileNotFoundError(f"Gateway CSV not found at {gw_path}")
    if not os.path.exists(bank_path):
        raise FileNotFoundError(f"Bank CSV not found at {bank_path}")
    if not os.path.exists(ledger_path):
        raise FileNotFoundError(f"Ledger CSV not found at {ledger_path}")

    # Load Gateway
    df_gw = pd.read_csv(gw_path)
    if "gateway_timestamp" in df_gw.columns:
        df_gw["gateway_timestamp"] = pd.to_datetime(df_gw["gateway_timestamp"], errors="coerce")
    if "transaction_id" in df_gw.columns:
        df_gw = df_gw.set_index("transaction_id", drop=False)

    # Load Bank
    df_bank = pd.read_csv(bank_path)
    for col in ["bank_received_at", "bank_updated_at", "bank_timestamp"]:
        if col in df_bank.columns:
            df_bank[col] = pd.to_datetime(df_bank[col], errors="coerce")
    if "transaction_id" in df_bank.columns:
        df_bank = df_bank.set_index("transaction_id", drop=False)

    # Load Ledger
    df_ledger = pd.read_csv(ledger_path)
    if "ledger_timestamp" in df_ledger.columns:
        df_ledger["ledger_timestamp"] = pd.to_datetime(df_ledger["ledger_timestamp"], errors="coerce")
    if "transaction_id" in df_ledger.columns:
        df_ledger = df_ledger.set_index("transaction_id", drop=False)

    logger.info("Loaded dataset: Gateway (%d rows), Bank (%d rows), Ledger (%d rows)",
                len(df_gw), len(df_bank), len(df_ledger))

    return {
        "gateway": df_gw,
        "bank": df_bank,
        "ledger": df_ledger
    }
