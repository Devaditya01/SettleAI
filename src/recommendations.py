"""Deterministic recommendation engine.

Maps rule-engine root causes to support-agent actions and customer-safe
messages. This module is intentionally deterministic: no ML, no LLM, and no
randomness.
"""

from __future__ import annotations

from typing import TypedDict


class Recommendation(TypedDict):
    root_cause: str
    urgency: str
    action: str
    title: str
    description: str
    customer_message: str
    requires_escalation: bool
    do_not_refund_yet: bool


def _rec(
    root_cause: str,
    urgency: str,
    action: str,
    title: str,
    description: str,
    customer_message: str,
    requires_escalation: bool,
    do_not_refund_yet: bool,
) -> Recommendation:
    return {
        "root_cause": root_cause,
        "urgency": urgency,
        "action": action,
        "title": title,
        "description": description,
        "customer_message": customer_message,
        "requires_escalation": requires_escalation,
        "do_not_refund_yet": do_not_refund_yet,
    }


RECOMMENDATION_MAP: dict[str, Recommendation] = {
    "INCONSISTENT_TIMESTAMPS": _rec(
        "INCONSISTENT_TIMESTAMPS",
        "HIGH",
        "AUDIT_SYSTEM_CLOCKS",
        "Timestamp Anomaly Detected",
        "Sequence of events shows out-of-order timestamps. Audit partner system time synchronization before financial action.",
        "We detected an issue in the transaction record and are investigating it with our operations team.",
        True,
        True,
    ),
    "GATEWAY_FAILURE": _rec(
        "GATEWAY_FAILURE",
        "HIGH",
        "CHECK_GATEWAY_LOGS",
        "Gateway Processing Error",
        "Gateway failed before successful downstream settlement. Confirm the gateway response before advising retry or refund.",
        "Your payment could not be completed through the gateway. Please wait for confirmation before retrying.",
        False,
        False,
    ),
    "BANK_FAILURE": _rec(
        "BANK_FAILURE",
        "HIGH",
        "INITIATE_REFUND_OR_RETRY",
        "Payment Failed at Bank",
        "Bank explicitly rejected the settlement attempt. Verify failure reason and follow the standard refund or retry workflow.",
        "The bank rejected this payment attempt. Our team will guide the next safe step.",
        False,
        False,
    ),
    "AMOUNT_MISMATCH": _rec(
        "AMOUNT_MISMATCH",
        "HIGH",
        "FLAG_FOR_RECONCILIATION",
        "Reconciliation Variance",
        "Gateway, bank, and ledger amounts do not match. Raise a reconciliation ticket before any additional payout or refund.",
        "We are reviewing your payment to make sure the correct amount is settled.",
        True,
        True,
    ),
    "MISSING_GATEWAY_RECORD": _rec(
        "MISSING_GATEWAY_RECORD",
        "HIGH",
        "VERIFY_TRANSACTION_ID",
        "Unrecognized Transaction",
        "No gateway record exists for this transaction ID. Verify the ID and check for orphaned bank or ledger records.",
        "We could not find this transaction ID in the payment gateway records. Please verify the ID.",
        True,
        True,
    ),
    "MISSING_BANK_RECORD": _rec(
        "MISSING_BANK_RECORD",
        "MEDIUM",
        "QUERY_BANK_NODE",
        "Missing Bank Confirmation",
        "Gateway evidence exists but bank settlement evidence is missing. Query bank/webhook records; do not assume failure.",
        "Your payment is being verified with our banking partner. We will update you once the bank outcome is confirmed.",
        True,
        True,
    ),
    "MISSING_LEDGER_RECORD": _rec(
        "MISSING_LEDGER_RECORD",
        "MEDIUM",
        "TRIGGER_LEDGER_SYNC_CHECK",
        "Missing Ledger Posting",
        "Bank evidence exists but ledger posting is missing. Check ledger sync and reconciliation jobs.",
        "The bank outcome is available, and we are checking final ledger posting.",
        False,
        True,
    ),
    "SETTLED_SUCCESSFULLY": _rec(
        "SETTLED_SUCCESSFULLY",
        "LOW",
        "NO_ACTION_REQUIRED",
        "Settlement Complete",
        "Transaction is reconciled across gateway, bank, and ledger. No operational action is required.",
        "Your payment has been successfully processed and settled.",
        False,
        False,
    ),
    "BANK_PROCESSING_DELAY": _rec(
        "BANK_PROCESSING_DELAY",
        "MEDIUM",
        "MONITOR_SLA_WINDOW",
        "Awaiting Bank Settlement",
        "Payment is still at the bank processing stage. Monitor SLA and contact bank operations if the delay continues.",
        "Your payment is taking longer than usual due to bank processing. We are monitoring it.",
        False,
        True,
    ),
    "LEDGER_POSTING_DELAY": _rec(
        "LEDGER_POSTING_DELAY",
        "LOW",
        "TRIGGER_LEDGER_SYNC",
        "Ledger Sync Pending",
        "Bank settlement is available but ledger posting is delayed. Trigger or monitor ledger reconciliation.",
        "Your payment has reached the bank and is being finalized in our system.",
        False,
        True,
    ),
    "DUPLICATE_RETRY_SUSPECTED": _rec(
        "DUPLICATE_RETRY_SUSPECTED",
        "HIGH",
        "VERIFY_IDEMPOTENCY",
        "Multiple Payment Attempts",
        "Retry activity was detected. Check idempotency and bank credits before taking any refund or retry action.",
        "We are checking the payment attempts to make sure only one valid charge is applied.",
        True,
        True,
    ),
    "UNDETERMINED": _rec(
        "UNDETERMINED",
        "MEDIUM",
        "ESCALATE_TO_ENGINEERING",
        "Undetermined State",
        "Automated diagnosis could not determine a root cause. Review gateway, bank, and ledger records manually.",
        "We are investigating your transaction and will provide an update as soon as possible.",
        True,
        True,
    ),
}

_ALIASES = {
    "SUCCESSFUL_SETTLEMENT": "SETTLED_SUCCESSFULLY",
    "DEFINITIVE_FAILURE": "BANK_FAILURE",
    "MISSING_EVIDENCE": "MISSING_BANK_RECORD",
    "RETRY_DUPLICATE": "DUPLICATE_RETRY_SUSPECTED",
    "DUPLICATE_RETRY": "DUPLICATE_RETRY_SUSPECTED",
    "INVALID_EVIDENCE": "INCONSISTENT_TIMESTAMPS",
}

_UNKNOWN_FALLBACK = _rec(
    "UNKNOWN",
    "MEDIUM",
    "MANUAL_REVIEW_REQUIRED",
    "Manual Review Required",
    "Unknown root cause received. Manual review is required before financial action.",
    "We are reviewing your transaction and will be in touch shortly.",
    True,
    True,
)


def get_recommendation(root_cause: str) -> Recommendation:
    """Return the deterministic recommendation for a rule-engine root cause."""
    if not isinstance(root_cause, str):
        return _UNKNOWN_FALLBACK

    normalized = root_cause.strip().upper()
    normalized = _ALIASES.get(normalized, normalized)
    recommendation = RECOMMENDATION_MAP.get(normalized)
    if recommendation is not None:
        return recommendation

    fallback = dict(_UNKNOWN_FALLBACK)
    fallback["root_cause"] = root_cause
    return Recommendation(**fallback)  # type: ignore[misc]


def get_all_causes() -> list[str]:
    """Return all root causes directly covered by the lookup table."""
    return list(RECOMMENDATION_MAP.keys())


def is_valid_cause(root_cause: str) -> bool:
    """Return True when a root cause is covered directly or through an alias."""
    if not isinstance(root_cause, str):
        return False
    normalized = root_cause.strip().upper()
    return normalized in RECOMMENDATION_MAP or normalized in _ALIASES
