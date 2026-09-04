"""
Journey builder for the Settlement Intelligence Agent.

Takes the trace dict produced by ``tracer.trace_transaction()``
and computes the elapsed times (in minutes) between each system
hop in the settlement pipeline:

    Gateway → Bank (Hop 1)
    Bank Received → Bank Updated (Hop 2 — internal processing)
    Bank Updated → Ledger (Hop 3)
    Gateway → Ledger (Total end-to-end)

Missing timestamps produce ``None`` — never ``0``.
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _elapsed_minutes(
    start: datetime | None,
    end: datetime | None,
    hop_name: str,
    tx_id: str,
) -> float | None:
    """Compute (end - start) in minutes, or None if either is missing.

    Logs a warning when the result is negative (data anomaly).
    """
    if start is None or end is None:
        return None

    delta: timedelta = end - start
    minutes = round(delta.total_seconds() / 60.0, 2)

    if minutes < 0:
        logger.warning(
            "Transaction '%s': negative elapsed time for %s (%.2f min). "
            "Possible data anomaly.",
            tx_id, hop_name, minutes,
        )

    return minutes


def _extract_timestamp(source_dict: dict | None, key: str) -> datetime | None:
    """Safely pull a timestamp from a trace source dict."""
    if source_dict is None:
        return None
    value = source_dict.get(key)
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_journey(trace: dict) -> dict:
    """Compute elapsed times between settlement system hops.

    Args:
        trace:  The dict returned by ``tracer.trace_transaction()``,
                containing ``"transaction_id"``, ``"gateway"``,
                ``"bank"``, and ``"ledger"`` keys.

    Returns:
        A dict with the shape::

            {
                "transaction_id":  str,

                # Extracted timestamps (datetime | None)
                "gateway_timestamp":  ...,
                "bank_received_at":   ...,
                "bank_updated_at":    ...,
                "ledger_timestamp":   ...,

                # Elapsed times in minutes (float | None)
                "gateway_to_bank_minutes":   ...,   # Hop 1
                "bank_processing_minutes":   ...,   # Hop 2
                "bank_to_ledger_minutes":     ...,   # Hop 3
                "total_elapsed_minutes":      ...,   # End-to-end

                # Convenience flags
                "gateway_found": bool,
                "bank_found":    bool,
                "ledger_found":  bool,
            }
    """
    tx_id = trace["transaction_id"]

    # --- Extract timestamps ---
    gateway_ts = _extract_timestamp(trace["gateway"], "gateway_timestamp")
    bank_received = _extract_timestamp(trace["bank"], "bank_received_at")
    bank_updated = _extract_timestamp(trace["bank"], "bank_updated_at")
    ledger_ts = _extract_timestamp(trace["ledger"], "ledger_timestamp")

    # --- Compute hops ---
    hop1 = _elapsed_minutes(gateway_ts, bank_received, "gateway_to_bank", tx_id)
    hop2 = _elapsed_minutes(bank_received, bank_updated, "bank_processing", tx_id)
    hop3 = _elapsed_minutes(bank_updated, ledger_ts, "bank_to_ledger", tx_id)
    total = _elapsed_minutes(gateway_ts, ledger_ts, "total_elapsed", tx_id)

    return {
        "transaction_id": tx_id,

        # Timestamps
        "gateway_timestamp": gateway_ts,
        "bank_received_at": bank_received,
        "bank_updated_at": bank_updated,
        "ledger_timestamp": ledger_ts,

        # Elapsed times (minutes)
        "gateway_to_bank_minutes": hop1,
        "bank_processing_minutes": hop2,
        "bank_to_ledger_minutes": hop3,
        "total_elapsed_minutes": total,

        # Convenience flags
        "gateway_found": trace["gateway"] is not None,
        "bank_found": trace["bank"] is not None,
        "ledger_found": trace["ledger"] is not None,
    }
