"""
Service Orchestration module for SettleAI (Phase 14).

Master integration module providing ``analyze_transaction()``.
Unifies trace, journey, rules engine, exception handling, recommendations,
ML delay risk prediction, and historical ETA estimation into a single,
schema-validated response contract.

Failure Isolation:
ML risk predictions and ETA estimations are wrapped in strict try/except blocks.
If ML feature extraction or prediction fails, or if ETA matching fails,
the primary deterministic flow continues uninterrupted with safe fallback values.
"""

from __future__ import annotations

import logging
from typing import Any

from src.validator import validate_transaction_id
from src.loader import load_data
from src.tracer import trace_transaction
from src.journey import build_journey
from src.rules import apply_rules
from src.exceptions import evaluate_exceptions
from src.recommendations import get_recommendation

logger = logging.getLogger(__name__)


def analyze_transaction(
    transaction_id: str,
    data_dir: str = "data",
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Master orchestration function for SettleAI transaction analysis.

    Args:
        transaction_id: Transaction ID string to analyze.
        data_dir: Directory containing gateway.csv, bank.csv, ledger.csv.
        data: Pre-loaded dataset dict from ``loader.load_data()`` (optional).

    Returns:
        A unified analysis contract dictionary.
    """
    # 1. Input Validation
    clean_tx_id = validate_transaction_id(transaction_id)

    # 2. Data Loading (cached or passed)
    if data is None:
        data = load_data(data_dir)

    # 3. Transaction Trace
    trace = trace_transaction(clean_tx_id, data)

    # 4. Hop Journey & Latency Calculation
    journey = build_journey(trace)

    # 5. Deterministic Rules Diagnosis
    rules_result = apply_rules(journey, trace)
    status = rules_result["status"]
    root_cause = rules_result["root_cause"]

    # 6. Exception Auditing & Evidence Confidence
    exceptions_result = evaluate_exceptions(journey, trace, rules_result)
    confidence = exceptions_result["evidence_confidence"]
    exceptions_list = exceptions_result["exceptions"]

    # 7. Actionable Operational Recommendation
    recommendation = get_recommendation(root_cause)

    # 8. ML Delay Risk Prediction (with Failure Isolation)
    ml_prediction = _run_ml_prediction_isolated(clean_tx_id, data, status)

    # 9. ETA Remaining Delay Estimation (with Failure Isolation)
    eta_estimation = _run_eta_estimation_isolated(trace, data_dir, status)

    # 10. Extract Gateway Summary for Header
    gw = trace.get("gateway") or {}
    gateway_summary = {
        "transaction_id": clean_tx_id,
        "amount": gw.get("amount"),
        "payment_method": gw.get("payment_method"),
        "gateway_timestamp": str(gw.get("gateway_timestamp")) if gw.get("gateway_timestamp") else None,
        "gateway_status": gw.get("gateway_status"),
    }

    return {
        "transaction_id": clean_tx_id,
        "gateway_summary": gateway_summary,
        "status": status,
        "root_cause": root_cause,
        "evidence_confidence": confidence,
        "exceptions": exceptions_list,
        "recommendation": recommendation,
        "journey": journey,
        "ml_prediction": ml_prediction,
        "eta_estimation": eta_estimation,
        "trace": trace,
    }


# ---------------------------------------------------------------------------
# Internal Failure-Isolated Helpers
# ---------------------------------------------------------------------------

def _run_ml_prediction_isolated(
    tx_id: str,
    data: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    """Execute ML delay risk prediction with failure isolation."""
    # ML prediction is only applicable if the transaction is in-progress / processing / at-risk
    if status not in {"PROCESSING", "AT_RISK"}:
        return {
            "applicable": False,
            "risk_score": None,
            "risk_level": "N/A",
            "predicted_delayed": None,
            "threshold_used": None,
            "model_version": None,
            "reason": f"Transaction status is {status}; ML delay prediction only applies to in-progress transactions.",
        }

    try:
        from src.ml_features import extract_features
        from src.predictor import predict_delay_risk

        features = extract_features(tx_id, data)
        return predict_delay_risk(features)
    except Exception as exc:
        logger.warning(
            "ML delay prediction failed for '%s' (failure isolated): %s",
            tx_id, exc,
        )
        return {
            "applicable": False,
            "risk_score": None,
            "risk_level": "UNKNOWN",
            "predicted_delayed": None,
            "threshold_used": None,
            "model_version": None,
            "reason": f"ML prediction unavailable: {exc}",
        }


def _run_eta_estimation_isolated(
    trace: dict[str, Any],
    data_dir: str,
    status: str,
) -> dict[str, Any]:
    """Execute ETA remaining delay estimation with failure isolation."""
    # ETA estimation is only applicable if the transaction is in-progress or delayed
    if status not in {"PROCESSING", "AT_RISK", "DELAYED"}:
        return {
            "applicable": False,
            "estimated_additional_delay_minutes": None,
            "median_final_settlement_minutes": None,
            "basis": None,
            "sample_size": 0,
            "confidence": "N/A",
            "reason": f"Transaction status is {status}; ETA estimation only applies to in-progress or delayed transactions.",
        }

    try:
        from src.estimator import estimate_additional_delay

        bank_name = trace.get("bank", {}).get("bank_name") if trace.get("bank") else None
        payment_method = trace.get("gateway", {}).get("payment_method") if trace.get("gateway") else None

        return estimate_additional_delay(
            bank_name=bank_name,
            payment_method=payment_method,
            data_dir=data_dir,
        )
    except Exception as exc:
        logger.warning(
            "ETA estimation failed (failure isolated): %s", exc
        )
        return {
            "applicable": False,
            "estimated_additional_delay_minutes": None,
            "median_final_settlement_minutes": None,
            "basis": None,
            "sample_size": 0,
            "confidence": "LOW",
            "reason": f"ETA estimation unavailable: {exc}",
        }
