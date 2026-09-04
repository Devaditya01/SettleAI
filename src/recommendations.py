"""
Recommendation Engine for the Settlement Intelligence Agent.

Maps deterministic root cause codes to clear, actionable support instructions
for operations and customer support analysts.
"""

RECOMMENDATION_MAP = {
    "SUCCESSFUL_SETTLEMENT": {
        "action": "NO_ACTION_REQUIRED",
        "title": "Settlement Complete",
        "description": "Payment was successfully processed across Gateway, Bank, and Ledger. Confirm settlement status with merchant."
    },
    "DEFINITIVE_FAILURE": {
        "action": "INITIATE_REFUND_OR_RETRY",
        "title": "Payment Failed at Bank",
        "description": "Bank explicitly rejected the payment. Notify merchant/customer to initiate a fresh payment attempt or refund if debited."
    },
    "GATEWAY_FAILURE": {
        "action": "CHECK_GATEWAY_LOGS",
        "title": "Gateway Processing Error",
        "description": "Gateway failed before reaching the bank. Advise customer to retry payment."
    },
    "AMOUNT_MISMATCH": {
        "action": "FLAG_FOR_RECONCILIATION",
        "title": "Reconciliation Variance",
        "description": "Settled/Ledger amount differs from Gateway captured amount. Flag to finance operations team for manual ledger adjustment."
    },
    "MISSING_BANK_RECORD": {
        "action": "QUERY_BANK_NODE",
        "title": "Missing Bank Confirmation",
        "description": "Gateway captured funds but bank has not recorded receipt. Ping bank webhooks or submit manual file inquiry."
    },
    "MISSING_GATEWAY_RECORD": {
        "action": "VERIFY_TRANSACTION_ID",
        "title": "Unrecognized Transaction",
        "description": "No gateway record found for this transaction ID. Verify ID accuracy or check for orphaned bank credits."
    },
    "BANK_PROCESSING_DELAY": {
        "action": "MONITOR_SLA_WINDOW",
        "title": "Awaiting Bank Settlement",
        "description": "Payment is currently undergoing bank clearance. Monitor SLA window before raising a bank ticket."
    },
    "LEDGER_POSTING_DELAY": {
        "action": "TRIGGER_LEDGER_SYNC",
        "title": "Ledger Sync Pending",
        "description": "Bank has confirmed credit but merchant ledger record is pending. Trigger async ledger sync job."
    },
    "DUPLICATE_RETRY": {
        "action": "VERIFY_IDEMPOTENCY",
        "title": "Multiple Payment Attempts",
        "description": "Multiple retry attempts detected. Check idempotency keys to ensure customer is not double-charged."
    },
    "INCONSISTENT_TIMESTAMPS": {
        "action": "AUDIT_SYSTEM_CLOCKS",
        "title": "Timestamp Anomaly Detected",
        "description": "Sequence of events shows timestamp out-of-order errors. Audit partner system time synchronization."
    },
    "UNDETERMINED": {
        "action": "ESCALATE_TO_ENGINEERING",
        "title": "Undetermined State",
        "description": "Complex transaction state. Escalate ticket to Tier-2 settlement engineering."
    }
}


def get_recommendation(root_cause: str) -> dict:
    """Retrieve operational recommendation for a given root cause.

    Args:
        root_cause: Deterministic root cause code from rules engine.

    Returns:
        Dict with 'action', 'title', and 'description'.
    """
    return RECOMMENDATION_MAP.get(
        root_cause,
        RECOMMENDATION_MAP["UNDETERMINED"]
    )
