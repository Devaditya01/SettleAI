"""
Deterministic rules engine for the Settlement Intelligence Agent.

Maps a transaction's journey and trace to:
  1. A product status  (SETTLED, FAILED, PROCESSING, AT_RISK, DELAYED, UNRESOLVED)
  2. A root cause      (priority-ordered deterministic rules)

No ML, no LLM — pure if/else logic.  The LLM does NOT decide the
root cause; this module does.
"""

import logging

from config import (
    SETTLEMENT_SLA_MINUTES,
    BANK_WARNING_MINUTES,
    LEDGER_WARNING_MINUTES,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Valid output vocabularies
# ---------------------------------------------------------------------------

VALID_STATUSES = {
    "SETTLED",
    "FAILED",
    "PROCESSING",
    "AT_RISK",
    "DELAYED",
    "UNRESOLVED",
}

VALID_ROOT_CAUSES = {
    "INCONSISTENT_TIMESTAMPS",
    "GATEWAY_FAILURE",
    "BANK_FAILURE",
    "AMOUNT_MISMATCH",
    "MISSING_GATEWAY_RECORD",
    "MISSING_BANK_RECORD",
    "MISSING_LEDGER_RECORD",
    "SETTLED_SUCCESSFULLY",
    "BANK_PROCESSING_DELAY",
    "LEDGER_POSTING_DELAY",
    "DUPLICATE_RETRY_SUSPECTED",
    "UNDETERMINED",
}

# Statuses that are "terminal" — SLA override does NOT apply.
_TERMINAL_STATUSES = {"SETTLED", "FAILED"}

# AT_RISK kicks in when total elapsed exceeds this fraction of the SLA.
_AT_RISK_THRESHOLD_FRACTION = 0.5


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_status(source_dict: dict | None, key: str) -> str | None:
    """Safely extract a status string from a trace source dict."""
    if source_dict is None:
        return None
    return source_dict.get(key)


def _get_amount(source_dict: dict | None, key: str) -> float | None:
    """Safely extract a monetary amount from a trace source dict."""
    if source_dict is None:
        return None
    val = source_dict.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _has_negative_elapsed(journey: dict) -> bool:
    """Check if any computed elapsed time is negative (data anomaly)."""
    for key in (
        "gateway_to_bank_minutes",
        "bank_processing_minutes",
        "bank_to_ledger_minutes",
        "total_elapsed_minutes",
    ):
        val = journey.get(key)
        if val is not None and val < 0:
            return True
    return False


def _amounts_match(gateway_amount, bank_amount, ledger_amount) -> bool:
    """Check that all available amounts are equal (exact comparison).

    Only compares pairs where both sides are not None.
    Returns True if no mismatch is found among available values.
    """
    pairs = []
    if gateway_amount is not None and bank_amount is not None:
        pairs.append((gateway_amount, bank_amount))
    if bank_amount is not None and ledger_amount is not None:
        pairs.append((bank_amount, ledger_amount))
    if gateway_amount is not None and ledger_amount is not None:
        pairs.append((gateway_amount, ledger_amount))

    return all(a == b for a, b in pairs)


# ---------------------------------------------------------------------------
# Public API — Status
# ---------------------------------------------------------------------------

def determine_status(journey: dict, trace: dict) -> str:
    """Map a transaction to a product status using deterministic rules.

    Waterfall logic:
      1. Classify a base status from statuses and presence flags.
      2. Override to DELAYED if total elapsed exceeds SLA (non-terminal only).
      3. Refine PROCESSING to AT_RISK if approaching SLA.

    Args:
        journey: Dict returned by ``journey.build_journey()``.
        trace:   Dict returned by ``tracer.trace_transaction()``.

    Returns:
        One of: SETTLED, FAILED, PROCESSING, AT_RISK, DELAYED, UNRESOLVED.
    """
    gateway_status = _get_status(trace["gateway"], "gateway_status")
    bank_status = _get_status(trace["bank"], "bank_status")
    ledger_status = _get_status(trace["ledger"], "ledger_status")

    gateway_found = journey["gateway_found"]
    bank_found = journey["bank_found"]
    ledger_found = journey["ledger_found"]

    total = journey.get("total_elapsed_minutes")

    # --- Step 1: Base status classification ---

    if not gateway_found:
        base = "UNRESOLVED"

    elif gateway_status == "FAILED":
        base = "FAILED"

    elif bank_found and bank_status == "FAILED":
        base = "FAILED"

    elif not bank_found and not ledger_found:
        # Gateway exists but neither bank nor ledger — can't determine.
        base = "UNRESOLVED"

    elif bank_status == "SETTLED" and ledger_status == "POSTED":
        base = "SETTLED"

    elif bank_found and bank_status == "PROCESSING":
        base = "PROCESSING"

    elif ledger_found and ledger_status == "PENDING":
        base = "PROCESSING"

    elif bank_status == "NOT_FOUND":
        base = "UNRESOLVED"

    else:
        base = "UNRESOLVED"

    # --- Step 2: DELAYED override (non-terminal only) ---

    if base not in _TERMINAL_STATUSES:
        if total is not None and total > SETTLEMENT_SLA_MINUTES:
            logger.info(
                "Transaction '%s': total %.2f min exceeds SLA (%d min) — "
                "overriding '%s' to DELAYED.",
                journey["transaction_id"], total, SETTLEMENT_SLA_MINUTES, base,
            )
            return "DELAYED"

    # --- Step 3: AT_RISK refinement ---

    at_risk_threshold = SETTLEMENT_SLA_MINUTES * _AT_RISK_THRESHOLD_FRACTION

    if base == "PROCESSING":
        if total is not None and total > at_risk_threshold:
            logger.info(
                "Transaction '%s': total %.2f min exceeds AT_RISK threshold "
                "(%.1f min) — refining PROCESSING to AT_RISK.",
                journey["transaction_id"], total, at_risk_threshold,
            )
            return "AT_RISK"

    return base


# ---------------------------------------------------------------------------
# Public API — Root Cause
# ---------------------------------------------------------------------------

def determine_root_cause(journey: dict, trace: dict) -> str:
    """Identify the root cause using priority-ordered deterministic rules.

    Priority chain (first match wins):
      1. Inconsistent/invalid timestamps
      2. Definitive failure (gateway or bank)
      3. Amount mismatch
      4. Missing evidence (bank, ledger, or gateway)
      5. Successful settlement
      6. Bank delay
      7. Ledger delay
      8. Retry/duplicate
      9. Undetermined

    Args:
        journey: Dict returned by ``journey.build_journey()``.
        trace:   Dict returned by ``tracer.trace_transaction()``.

    Returns:
        A root cause string from VALID_ROOT_CAUSES.
    """
    gateway_status = _get_status(trace["gateway"], "gateway_status")
    bank_status = _get_status(trace["bank"], "bank_status")
    ledger_status = _get_status(trace["ledger"], "ledger_status")

    gateway_found = journey["gateway_found"]
    bank_found = journey["bank_found"]
    ledger_found = journey["ledger_found"]

    gateway_amount = _get_amount(trace["gateway"], "amount")
    bank_amount = _get_amount(trace["bank"], "settlement_amount")
    ledger_amount = _get_amount(trace["ledger"], "ledger_amount")

    retry_count = 0
    if trace["gateway"] is not None:
        retry_count = trace["gateway"].get("retry_count", 0) or 0

    bank_processing = journey.get("bank_processing_minutes")
    bank_to_ledger = journey.get("bank_to_ledger_minutes")

    # --- Priority 1: Inconsistent/invalid timestamps ---
    if _has_negative_elapsed(journey):
        logger.warning(
            "Transaction '%s': negative elapsed time detected — "
            "INCONSISTENT_TIMESTAMPS.",
            journey["transaction_id"],
        )
        return "INCONSISTENT_TIMESTAMPS"

    # Check for gateway record existing but timestamp being None.
    if gateway_found and journey.get("gateway_timestamp") is None:
        return "INCONSISTENT_TIMESTAMPS"

    # --- Priority 2: Definitive failure ---
    if gateway_status == "FAILED":
        return "GATEWAY_FAILURE"

    if bank_status == "FAILED":
        return "BANK_FAILURE"

    # --- Priority 3: Amount mismatch ---
    if not _amounts_match(gateway_amount, bank_amount, ledger_amount):
        return "AMOUNT_MISMATCH"

    # --- Priority 4: Missing evidence ---
    if not gateway_found:
        return "MISSING_GATEWAY_RECORD"

    if not bank_found:
        return "MISSING_BANK_RECORD"

    if not ledger_found and bank_status == "SETTLED":
        return "MISSING_LEDGER_RECORD"

    # --- Priority 5: Successful settlement ---
    if (
        bank_status == "SETTLED"
        and ledger_status == "POSTED"
        and _amounts_match(gateway_amount, bank_amount, ledger_amount)
    ):
        return "SETTLED_SUCCESSFULLY"

    # --- Priority 6: Bank delay ---
    if bank_status == "PROCESSING":
        return "BANK_PROCESSING_DELAY"

    if bank_processing is not None and bank_processing > BANK_WARNING_MINUTES:
        return "BANK_PROCESSING_DELAY"

    # --- Priority 7: Ledger delay ---
    if bank_status == "SETTLED" and ledger_status == "PENDING":
        return "LEDGER_POSTING_DELAY"

    if bank_to_ledger is not None and bank_to_ledger > LEDGER_WARNING_MINUTES:
        return "LEDGER_POSTING_DELAY"

    # --- Priority 8: Retry/duplicate ---
    if retry_count > 0:
        return "DUPLICATE_RETRY_SUSPECTED"

    # --- Priority 9: Undetermined ---
    logger.info(
        "Transaction '%s': no deterministic rule matched — UNDETERMINED.",
        journey["transaction_id"],
    )
    return "UNDETERMINED"


# ---------------------------------------------------------------------------
# Public API — Convenience wrapper
# ---------------------------------------------------------------------------

def apply_rules(journey: dict, trace: dict) -> dict:
    """Run both status and root-cause determination.

    Args:
        journey: Dict returned by ``journey.build_journey()``.
        trace:   Dict returned by ``tracer.trace_transaction()``.

    Returns:
        {
            "status":     str,   # SETTLED | FAILED | PROCESSING | AT_RISK | DELAYED | UNRESOLVED
            "root_cause": str,   # e.g. BANK_PROCESSING_DELAY
        }
    """
    status = determine_status(journey, trace)
    root_cause = determine_root_cause(journey, trace)

    logger.info(
        "Transaction '%s': status=%s, root_cause=%s.",
        journey["transaction_id"], status, root_cause,
    )

    return {
        "status": status,
        "root_cause": root_cause,
    }
