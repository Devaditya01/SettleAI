"""
Exception handling and evidence confidence for the Settlement
Intelligence Agent.

Scans the trace, journey, and rules output for anomalies and
missing evidence, then:

  1. Builds an ``exceptions`` list of specific flags
     (e.g. ``BANK_RECORD_MISSING``, ``AMOUNT_MISMATCH``).
  2. Calculates an ``evidence_confidence`` level
     (``HIGH``, ``MEDIUM``, ``LOW``) based on how much
     evidence is available and trustworthy.

This module never invents data.  Missing evidence lowers
confidence — it does not get replaced with defaults.
"""

import logging

from config import BANK_WARNING_MINUTES, LEDGER_WARNING_MINUTES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Valid output vocabularies
# ---------------------------------------------------------------------------

VALID_CONFIDENCE_LEVELS = {"HIGH", "MEDIUM", "LOW"}

VALID_EXCEPTION_FLAGS = {
    # Missing records
    "GATEWAY_RECORD_MISSING",
    "BANK_RECORD_MISSING",
    "LEDGER_RECORD_MISSING",

    # Missing / unparseable timestamps
    "GATEWAY_TIMESTAMP_MISSING",
    "BANK_RECEIVED_TIMESTAMP_MISSING",
    "BANK_UPDATED_TIMESTAMP_MISSING",
    "LEDGER_TIMESTAMP_MISSING",

    # Data anomalies
    "INCONSISTENT_TIMESTAMPS",
    "AMOUNT_MISMATCH",

    # Operational flags
    "GATEWAY_FAILURE",
    "BANK_FAILURE",
    "BANK_PROCESSING_DELAY",
    "LEDGER_POSTING_DELAY",
    "DUPLICATE_RETRY_SUSPECTED",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_exceptions(journey: dict, trace: dict) -> list[str]:
    """Scan all available evidence and collect exception flags.

    Returns a deduplicated, sorted list of exception flag strings.
    """
    exceptions: list[str] = []

    # --- Missing records ---
    if not journey["gateway_found"]:
        exceptions.append("GATEWAY_RECORD_MISSING")
    if not journey["bank_found"]:
        exceptions.append("BANK_RECORD_MISSING")
    if not journey["ledger_found"]:
        exceptions.append("LEDGER_RECORD_MISSING")

    # --- Missing timestamps (record exists but timestamp is None/NaT) ---
    if journey["gateway_found"] and journey.get("gateway_timestamp") is None:
        exceptions.append("GATEWAY_TIMESTAMP_MISSING")

    if journey["bank_found"]:
        if journey.get("bank_received_at") is None:
            exceptions.append("BANK_RECEIVED_TIMESTAMP_MISSING")
        if journey.get("bank_updated_at") is None:
            exceptions.append("BANK_UPDATED_TIMESTAMP_MISSING")

    if journey["ledger_found"] and journey.get("ledger_timestamp") is None:
        exceptions.append("LEDGER_TIMESTAMP_MISSING")

    # --- Negative elapsed times (data anomaly) ---
    for key in (
        "gateway_to_bank_minutes",
        "bank_processing_minutes",
        "bank_to_ledger_minutes",
        "total_elapsed_minutes",
    ):
        val = journey.get(key)
        if val is not None and val < 0:
            if "INCONSISTENT_TIMESTAMPS" not in exceptions:
                exceptions.append("INCONSISTENT_TIMESTAMPS")
            break

    # --- Amount mismatch ---
    gw_amount = _safe_amount(trace["gateway"], "amount")
    bk_amount = _safe_amount(trace["bank"], "settlement_amount")
    lg_amount = _safe_amount(trace["ledger"], "ledger_amount")

    pairs = []
    if gw_amount is not None and bk_amount is not None:
        pairs.append((gw_amount, bk_amount))
    if bk_amount is not None and lg_amount is not None:
        pairs.append((bk_amount, lg_amount))
    if gw_amount is not None and lg_amount is not None:
        pairs.append((gw_amount, lg_amount))

    if any(a != b for a, b in pairs):
        exceptions.append("AMOUNT_MISMATCH")

    # --- Gateway failure ---
    if trace["gateway"] is not None:
        if trace["gateway"].get("gateway_status") == "FAILED":
            exceptions.append("GATEWAY_FAILURE")

    # --- Bank failure ---
    if trace["bank"] is not None:
        if trace["bank"].get("bank_status") == "FAILED":
            exceptions.append("BANK_FAILURE")

    # --- Bank processing delay ---
    bank_processing = journey.get("bank_processing_minutes")
    if bank_processing is not None and bank_processing > BANK_WARNING_MINUTES:
        exceptions.append("BANK_PROCESSING_DELAY")
    elif trace["bank"] is not None and trace["bank"].get("bank_status") == "PROCESSING":
        exceptions.append("BANK_PROCESSING_DELAY")

    # --- Ledger posting delay ---
    bank_to_ledger = journey.get("bank_to_ledger_minutes")
    if bank_to_ledger is not None and bank_to_ledger > LEDGER_WARNING_MINUTES:
        exceptions.append("LEDGER_POSTING_DELAY")
    elif (
        trace["bank"] is not None
        and trace["bank"].get("bank_status") == "SETTLED"
        and trace["ledger"] is not None
        and trace["ledger"].get("ledger_status") == "PENDING"
    ):
        exceptions.append("LEDGER_POSTING_DELAY")

    # --- Duplicate / retry ---
    if trace["gateway"] is not None:
        retry_count = trace["gateway"].get("retry_count", 0) or 0
        if retry_count > 0:
            exceptions.append("DUPLICATE_RETRY_SUSPECTED")

    return sorted(set(exceptions))


def _safe_amount(source_dict: dict | None, key: str) -> float | None:
    """Safely extract a monetary amount."""
    if source_dict is None:
        return None
    val = source_dict.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Internal helpers — Confidence
# ---------------------------------------------------------------------------

def _calculate_confidence(
    journey: dict,
    trace: dict,
    exceptions: list[str],
) -> str:
    """Determine evidence confidence based on missing fields and anomalies.

    Rules:
      LOW — Any core record missing (gateway or bank), OR
            inconsistent timestamps, OR
            gateway failure with no downstream data.
      MEDIUM — All core records present but ledger missing, OR
               any timestamp within a record is None, OR
               amount mismatch detected.
      HIGH — All three records present, all timestamps valid,
             no anomalies.
    """
    # --- LOW conditions ---
    low_flags = {
        "GATEWAY_RECORD_MISSING",
        "BANK_RECORD_MISSING",
        "INCONSISTENT_TIMESTAMPS",
    }
    if low_flags & set(exceptions):
        return "LOW"

    # Gateway failure with no bank/ledger → LOW
    if "GATEWAY_FAILURE" in exceptions:
        if not journey["bank_found"] or not journey["ledger_found"]:
            return "LOW"

    # --- MEDIUM conditions ---
    medium_flags = {
        "LEDGER_RECORD_MISSING",
        "GATEWAY_TIMESTAMP_MISSING",
        "BANK_RECEIVED_TIMESTAMP_MISSING",
        "BANK_UPDATED_TIMESTAMP_MISSING",
        "LEDGER_TIMESTAMP_MISSING",
        "AMOUNT_MISMATCH",
    }
    if medium_flags & set(exceptions):
        return "MEDIUM"

    # --- HIGH ---
    return "HIGH"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_exceptions(
    journey: dict,
    trace: dict,
    rules_result: dict,
) -> dict:
    """Calculate evidence confidence and collect exceptions.

    Args:
        journey:      Dict from ``journey.build_journey()``.
        trace:        Dict from ``tracer.trace_transaction()``.
        rules_result: Dict from ``rules.apply_rules()`` with keys
                      ``"status"`` and ``"root_cause"``.

    Returns:
        {
            "evidence_confidence": str,   # HIGH | MEDIUM | LOW
            "exceptions": list[str],      # sorted exception flags
        }
    """
    exceptions = _collect_exceptions(journey, trace)
    confidence = _calculate_confidence(journey, trace, exceptions)

    logger.info(
        "Transaction '%s': confidence=%s, exceptions=%s.",
        journey["transaction_id"], confidence, exceptions,
    )

    return {
        "evidence_confidence": confidence,
        "exceptions": exceptions,
    }
