"""
src/llm/deterministic.py
Rule-based fallback explanation generator.
Makes zero API calls. Always succeeds. Never hallucinated data.
"""
from __future__ import annotations
from .schema import LLMResponse
from ..recommendations import get_recommendation


# Human-readable root cause labels
_CAUSE_LABELS: dict[str, str] = {
    "BANK_PROCESSING_DELAY":   "a delay in bank processing",
    "LEDGER_POSTING_DELAY":    "a delay in ledger posting",
    "AMOUNT_MISMATCH":         "an amount mismatch between gateway and bank records",
    "MISSING_EVIDENCE":        "missing evidence from one or more settlement systems",
    "INVALID_EVIDENCE":        "invalid or inconsistent evidence records",
    "DEFINITIVE_FAILURE":      "a definitive payment failure confirmed by the gateway",
    "RETRY_DUPLICATE":         "a detected duplicate or retry attempt",
    "SUCCESSFUL_SETTLEMENT":   "successful reconciliation across all systems",
    "UNDETERMINED":            "an undetermined root cause requiring manual review",
    "UNKNOWN":                 "an unclassified event",
}

_STATUS_LABELS: dict[str, str] = {
    "SETTLED":    "fully settled and reconciled",
    "DELAYED":    "delayed beyond the expected SLA",
    "FAILED":     "confirmed as failed",
    "PENDING":    "still in progress",
    "AT_RISK":    "at risk of delay",
    "PROCESSING": "currently processing",
    "UNRESOLVED": "unresolved due to missing data",
    "UNKNOWN":    "in an unknown state",
}


def generate_deterministic(evidence_packet: dict) -> LLMResponse:
    """
    Produce a validated LLMResponse from the structured evidence packet
    without calling any external API.

    Args:
        evidence_packet: Dict containing transaction_id, status, root_cause,
                         confidence, elapsed_minutes, exceptions,
                         and recommended_action.

    Returns:
        LLMResponse with provider_used="deterministic" and is_fallback=True.
    """
    status     = str(evidence_packet.get("status", "UNKNOWN")).upper()
    root_cause = str(evidence_packet.get("root_cause", "UNKNOWN")).upper()
    confidence = str(evidence_packet.get("confidence", "LOW")).upper()
    elapsed    = evidence_packet.get("elapsed_minutes", 0.0)
    exceptions = evidence_packet.get("exceptions", []) or []
    tx_id      = evidence_packet.get("transaction_id", "N/A")

    # Get deterministic recommendation (from recommendations.py)
    rec = get_recommendation(root_cause)
    action = rec.get("action") or evidence_packet.get("recommended_action", "Manual investigation required.")

    status_label = _STATUS_LABELS.get(status, "in an unknown state")
    cause_label  = _CAUSE_LABELS.get(root_cause, "an unclassified event")

    explanation_parts = [
        f"Transaction {tx_id} is {status_label}.",
        f"The root cause has been identified as {cause_label}.",
    ]

    if elapsed and float(elapsed) > 0:
        explanation_parts.append(
            f"The transaction has been in processing for {float(elapsed):.1f} minutes."
        )

    if exceptions:
        explanation_parts.append(
            f"Notable exceptions: {', '.join(exceptions)}."
        )

    explanation_parts.append(f"Confidence level: {confidence}.")

    return LLMResponse(
        status=status,
        root_cause=root_cause,
        confidence=confidence,
        elapsed_minutes=float(elapsed),
        explanation=" ".join(explanation_parts),
        recommended_action=action,
        exception_list=list(exceptions),
        provider_used="deterministic",
        is_fallback=True,
        fallback_reason="All AI providers unavailable — rule-based analysis used.",
    )
