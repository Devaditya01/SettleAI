"""Historical ETA estimator for Phase 12.

This is deliberately not another ML model. It uses delayed historical
settlements to estimate the remaining time from the configured prediction
checkpoint, with transparent fallback behavior when an exact segment is thin.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd

from config import (
    DATA_DIR,
    PREDICTION_CHECKPOINT_MINUTES,
    SETTLEMENT_SLA_MINUTES,
)
from src.ml_features import load_feature_sources


MIN_EXACT_SAMPLES = 10
MIN_FALLBACK_SAMPLES = 10


def _normalize_category(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    return cleaned or None


def _minutes_between(later: pd.Series, earlier: pd.Series) -> pd.Series:
    return (later - earlier).dt.total_seconds() / 60.0


def _confidence(sample_size: int, basis: str) -> str:
    if basis == "bank_and_payment_method" and sample_size >= 20:
        return "HIGH"
    if sample_size >= 10:
        return "MEDIUM"
    return "LOW"


def _unavailable_response(reason: str) -> dict[str, Any]:
    return {
        "applicable": False,
        "estimated_additional_delay_minutes": None,
        "median_final_settlement_minutes": None,
        "basis": None,
        "sample_size": 0,
        "confidence": "LOW",
        "reason": reason,
    }


@lru_cache(maxsize=1)
def _delayed_history(data_dir: str = DATA_DIR) -> pd.DataFrame:
    gateway, bank, ledger = load_feature_sources(data_dir)

    merged = gateway.merge(bank, on="transaction_id", how="left").merge(
        ledger, on="transaction_id", how="left"
    )

    ledger_posted = (
        merged["ledger_status"].eq("POSTED") & merged["ledger_timestamp"].notna()
    )
    final_settlement_minutes = _minutes_between(
        merged["ledger_timestamp"], merged["gateway_timestamp"]
    )

    delayed = (
        merged["gateway_status"].eq("SUCCESS")
        & ledger_posted
        & final_settlement_minutes.gt(SETTLEMENT_SLA_MINUTES)
        & merged["bank_name"].notna()
        & merged["payment_method"].notna()
    )

    history = pd.DataFrame(
        {
            "bank_name": merged.loc[delayed, "bank_name"].astype(str).str.upper(),
            "payment_method": merged.loc[delayed, "payment_method"]
            .astype(str)
            .str.upper(),
            "final_settlement_minutes": final_settlement_minutes.loc[delayed],
        }
    )
    history["additional_delay_minutes"] = (
        history["final_settlement_minutes"] - PREDICTION_CHECKPOINT_MINUTES
    ).clip(lower=0)

    return history.reset_index(drop=True)


def _segment_estimate(history: pd.DataFrame, mask: pd.Series, basis: str) -> dict[str, Any]:
    segment = history.loc[mask]
    sample_size = len(segment)

    return {
        "applicable": True,
        "estimated_additional_delay_minutes": round(
            float(segment["additional_delay_minutes"].median()), 1
        ),
        "median_final_settlement_minutes": round(
            float(segment["final_settlement_minutes"].median()), 1
        ),
        "basis": basis,
        "sample_size": sample_size,
        "confidence": _confidence(sample_size, basis),
        "reason": None,
    }


def estimate_additional_delay(
    bank_name: str | None,
    payment_method: str | None,
    data_dir: str = DATA_DIR,
) -> dict[str, Any]:
    """Estimate remaining delay from historical delayed settlements.

    Args:
        bank_name: Bank segment for the in-progress transaction.
        payment_method: Payment method segment for the in-progress transaction.
        data_dir: Source data directory. Defaults to project data/.

    Returns:
        A deterministic ETA packet that states which historical segment was used.
    """
    normalized_bank = _normalize_category(bank_name)
    normalized_method = _normalize_category(payment_method)

    if not normalized_bank and not normalized_method:
        return _unavailable_response("bank_name or payment_method is required.")

    history = _delayed_history(data_dir)
    if history.empty:
        return _unavailable_response("No delayed settlement history is available.")

    if normalized_bank and normalized_method:
        exact_mask = (
            history["bank_name"].eq(normalized_bank)
            & history["payment_method"].eq(normalized_method)
        )
        if int(exact_mask.sum()) >= MIN_EXACT_SAMPLES:
            return _segment_estimate(history, exact_mask, "bank_and_payment_method")

    if normalized_bank:
        bank_mask = history["bank_name"].eq(normalized_bank)
        if int(bank_mask.sum()) >= MIN_FALLBACK_SAMPLES:
            return _segment_estimate(history, bank_mask, "bank")

    if normalized_method:
        method_mask = history["payment_method"].eq(normalized_method)
        if int(method_mask.sum()) >= MIN_FALLBACK_SAMPLES:
            return _segment_estimate(history, method_mask, "payment_method")

    global_mask = pd.Series(True, index=history.index)
    return _segment_estimate(history, global_mask, "global")
