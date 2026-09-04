"""
Transaction tracer for the Settlement Intelligence Agent.

Locates a single transaction across Gateway, Bank, and Ledger
DataFrames and returns a unified trace dict.  Missing records
are represented as None — never fabricated.

No other module should perform raw DataFrame lookups.
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_lookup(df: pd.DataFrame, tx_id: str, source_name: str) -> dict | None:
    """Look up tx_id in an indexed DataFrame.

    Returns a plain dict of the row, or None if the transaction
    does not exist in this source.  If duplicates are present,
    takes the first row and logs a warning.
    """
    if tx_id not in df.index:
        return None

    row = df.loc[tx_id]

    # Handle duplicate transaction_ids: loc returns a DataFrame
    # instead of a Series when there are multiple matches.
    if isinstance(row, pd.DataFrame):
        logger.warning(
            "%s contains %d rows for '%s'; using the first.",
            source_name, len(row), tx_id,
        )
        row = row.iloc[0]

    return _sanitize_row(row.to_dict())


def _sanitize_row(row_dict: dict) -> dict:
    """Convert pandas types to native Python for JSON safety.

    * pd.Timestamp  → datetime
    * pd.NaT        → None
    * np.int64/float64 → int/float
    """
    clean = {}
    for key, value in row_dict.items():
        if isinstance(value, pd.Timestamp):
            clean[key] = value.to_pydatetime() if not pd.isna(value) else None
        elif pd.isna(value):
            clean[key] = None
        else:
            # Convert numpy scalars to native Python types
            try:
                clean[key] = value.item()
            except (AttributeError, ValueError):
                clean[key] = value
    return clean


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def trace_transaction(tx_id: str, data: dict) -> dict:
    """Locate a transaction across all three settlement systems.

    Args:
        tx_id:  A validated transaction ID string (already passed
                through ``validator.validate_transaction_id``).
        data:   The dict returned by ``loader.load_data()`` with keys
                ``"gateway"``, ``"bank"``, ``"ledger"``, each holding
                a pandas DataFrame indexed by ``transaction_id``.

    Returns:
        A dict with the shape::

            {
                "transaction_id": str,
                "gateway": dict | None,
                "bank":    dict | None,
                "ledger":  dict | None,
            }

        Each source value is either a plain dict of the row's
        columns (with native Python types) or ``None`` when the
        transaction has no record in that system.
    """
    gateway_row = _safe_lookup(data["gateway"], tx_id, "gateway")
    bank_row = _safe_lookup(data["bank"], tx_id, "bank")
    ledger_row = _safe_lookup(data["ledger"], tx_id, "ledger")

    found = []
    if gateway_row is not None:
        found.append("gateway")
    if bank_row is not None:
        found.append("bank")
    if ledger_row is not None:
        found.append("ledger")

    if not found:
        logger.warning("Transaction '%s' not found in any system.", tx_id)
    else:
        logger.info(
            "Transaction '%s' found in: %s.", tx_id, ", ".join(found)
        )

    return {
        "transaction_id": tx_id,
        "gateway": gateway_row,
        "bank": bank_row,
        "ledger": ledger_row,
    }
