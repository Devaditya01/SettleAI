"""
Phase 13 — Recommendations Engine
===================================
Deterministic lookup: root_cause (str) → recommended action, urgency, and
customer-safe message.

No ML, no LLM, no randomness.  Same input → same output every time.
Consumed by Phase 14 (service.py) and Phase 15 (llm.py).
"""

from __future__ import annotations

from typing import TypedDict


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class Recommendation(TypedDict):
    root_cause: str
    urgency: str                  # "HIGH" | "MEDIUM" | "LOW"
    action: str                   # Internal action for support agent
    customer_message: str         # Safe, non-technical message for customer
    requires_escalation: bool     # True if a human supervisor must be looped in
    do_not_refund_yet: bool       # Hard guard: True means hold any refund action


# ---------------------------------------------------------------------------
# Lookup Table
# ---------------------------------------------------------------------------

_RECOMMENDATIONS: dict[str, Recommendation] = {

    "INVALID_EVIDENCE": Recommendation(
        root_cause="INVALID_EVIDENCE",
        urgency="HIGH",
        action=(
            "Flag transaction for manual data review. "
            "Evidence records contain inconsistencies (e.g. duplicate IDs, "
            "conflicting timestamps). Do not take financial action until resolved."
        ),
        customer_message=(
            "We have detected an issue with your transaction record and are "
            "investigating. Our team will update you within 2 hours."
        ),
        requires_escalation=True,
        do_not_refund_yet=True,
    ),

    "DEFINITIVE_FAILURE": Recommendation(
        root_cause="DEFINITIVE_FAILURE",
        urgency="HIGH",
        action=(
            "Transaction confirmed as failed. Initiate the standard refund "
            "workflow. Do NOT retry the payment — gateway has returned a "
            "definitive failure response code."
        ),
        customer_message=(
            "Your payment was unsuccessful. No amount has been deducted. "
            "If you see a hold on your account, it will be released within 3–5 business days."
        ),
        requires_escalation=False,
        do_not_refund_yet=False,
    ),

    "AMOUNT_MISMATCH": Recommendation(
        root_cause="AMOUNT_MISMATCH",
        urgency="HIGH",
        action=(
            "Amount credited by bank does not match expected settlement. "
            "Raise a reconciliation ticket immediately. "
            "DO NOT process a refund until the discrepancy is resolved — "
            "the difference may indicate a duplicate or partial credit."
        ),
        customer_message=(
            "We are reviewing your payment to ensure the correct amount was "
            "processed. Our reconciliation team will contact you within 24 hours."
        ),
        requires_escalation=True,
        do_not_refund_yet=True,
    ),

    "MISSING_EVIDENCE": Recommendation(
        root_cause="MISSING_EVIDENCE",
        urgency="MEDIUM",
        action=(
            "Bank settlement record is missing. Escalate to the gateway team "
            "to confirm whether a payout was initiated. "
            "Do not assume failure — the bank may have processed and not reported yet."
        ),
        customer_message=(
            "Your payment is being verified with our banking partner. "
            "This typically resolves within 30–60 minutes."
        ),
        requires_escalation=True,
        do_not_refund_yet=True,
    ),

    "SUCCESSFUL_SETTLEMENT": Recommendation(
        root_cause="SUCCESSFUL_SETTLEMENT",
        urgency="LOW",
        action=(
            "Transaction has been fully reconciled across gateway, bank, and ledger. "
            "No action required."
        ),
        customer_message=(
            "Your payment has been successfully processed and settled."
        ),
        requires_escalation=False,
        do_not_refund_yet=False,
    ),

    "BANK_PROCESSING_DELAY": Recommendation(
        root_cause="BANK_PROCESSING_DELAY",
        urgency="MEDIUM",
        action=(
            "Payment has exceeded the standard SLA at the bank processing stage. "
            "Contact bank operations team with the transaction reference. "
            "Standard resolution time is 30–90 minutes."
        ),
        customer_message=(
            "Your payment is taking slightly longer than usual due to bank processing. "
            "No action is needed from your side — we are monitoring it."
        ),
        requires_escalation=False,
        do_not_refund_yet=True,
    ),

    "LEDGER_POSTING_DELAY": Recommendation(
        root_cause="LEDGER_POSTING_DELAY",
        urgency="LOW",
        action=(
            "Bank credit is confirmed. Ledger posting is delayed — likely a batch "
            "sync issue. Monitor for 15 minutes. If unresolved, trigger a manual "
            "ledger reconciliation job."
        ),
        customer_message=(
            "Your payment has been received by our banking partner and "
            "is being finalised in our system. This should complete shortly."
        ),
        requires_escalation=False,
        do_not_refund_yet=True,
    ),

    "RETRY_DUPLICATE": Recommendation(
        root_cause="RETRY_DUPLICATE",
        urgency="HIGH",
        action=(
            "Multiple payment attempts detected for the same transaction. "
            "Check for duplicate credits in the bank feed before taking any action. "
            "If a duplicate credit exists, initiate a reversal — not a refund."
        ),
        customer_message=(
            "We are reviewing your payment to ensure only one charge is applied. "
            "If any duplicate charge occurred, it will be reversed automatically."
        ),
        requires_escalation=True,
        do_not_refund_yet=True,
    ),

    "UNDETERMINED": Recommendation(
        root_cause="UNDETERMINED",
        urgency="MEDIUM",
        action=(
            "Automated diagnosis could not determine a root cause. "
            "Manual investigation required. Review all three records: "
            "gateway, bank, and ledger. Escalate to senior support if unresolved."
        ),
        customer_message=(
            "We are investigating your transaction and will provide an update "
            "as soon as possible."
        ),
        requires_escalation=True,
        do_not_refund_yet=True,
    ),
}

# Safe fallback for unknown/unexpected causes
_UNKNOWN_FALLBACK: Recommendation = Recommendation(
    root_cause="UNKNOWN",
    urgency="MEDIUM",
    action=(
        "Unknown root cause received. Manual review required. "
        "Do not take financial action until the transaction is fully assessed."
    ),
    customer_message=(
        "We are reviewing your transaction and will be in touch shortly."
    ),
    requires_escalation=True,
    do_not_refund_yet=True,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_recommendation(root_cause: str) -> Recommendation:
    """
    Return the deterministic recommendation for a given root_cause string.

    Never raises — unknown causes return a safe UNKNOWN fallback so the
    service layer never crashes due to an unexpected rule output.

    Args:
        root_cause: One of the defined root cause constants (e.g. "BANK_PROCESSING_DELAY").

    Returns:
        A Recommendation TypedDict with urgency, action, customer_message, and guard flags.
    """
    if not isinstance(root_cause, str):
        return _UNKNOWN_FALLBACK

    result = _RECOMMENDATIONS.get(root_cause.strip().upper())
    if result is None:
        fallback = dict(_UNKNOWN_FALLBACK)
        fallback["root_cause"] = root_cause  # preserve the original for logging
        return Recommendation(**fallback)     # type: ignore[misc]
    return result


def get_all_causes() -> list[str]:
    """Return the full list of valid root cause strings."""
    return list(_RECOMMENDATIONS.keys())


def is_valid_cause(root_cause: str) -> bool:
    """Return True if the root cause is defined in the lookup table."""
    return isinstance(root_cause, str) and root_cause.strip().upper() in _RECOMMENDATIONS
