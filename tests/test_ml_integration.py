"""Training-serving parity and backend ML integration tests."""

from __future__ import annotations

import math
import sys
import types

import pandas as pd
import pytest

from src.loader import load_data
from src.ml_features import (
    FEATURE_COLUMNS,
    build_training_table,
    extract_features,
)
from src.service import analyze_transaction


def _equal_with_missing(left, right) -> bool:
    if pd.isna(left) and pd.isna(right):
        return True
    if isinstance(left, float) or isinstance(right, float):
        try:
            return math.isclose(float(left), float(right), rel_tol=1e-9, abs_tol=1e-9)
        except (TypeError, ValueError):
            pass
    return left == right


def test_extract_features_returns_exact_model_contract():
    features = extract_features("TXN000042", data=load_data("data"))

    assert list(features) == FEATURE_COLUMNS
    assert "transaction_id" not in features
    assert "ledger_timestamp" not in features
    assert "bank_updated_at" not in features


def test_inference_features_match_training_features_at_checkpoint():
    data = load_data("data")
    training = build_training_table("data", include_ids=True).table

    # Compare several rows so observed, updated, and missing-bank states are
    # covered while keeping the test quick.
    sample = training.iloc[[0, len(training) // 2, len(training) - 1]]
    for _, expected in sample.iterrows():
        actual = extract_features(expected["transaction_id"], data=data)
        for feature in FEATURE_COLUMNS:
            assert _equal_with_missing(actual[feature], expected[feature]), (
                f"{expected['transaction_id']} differs on {feature}: "
                f"inference={actual[feature]!r}, training={expected[feature]!r}"
            )


def test_feature_extraction_hides_bank_update_after_checkpoint():
    data = load_data("data")
    features = extract_features("TXN000001", data=data)

    # Bank update occurs about 29 minutes after capture, so at the 10-minute
    # checkpoint only the pending bank observation is visible.
    assert features["bank_observed_by_checkpoint"] == 1
    assert features["bank_update_observed_by_checkpoint"] == 0
    assert features["bank_status_at_checkpoint"] == "PROCESSING"
    assert features["bank_response_code_at_checkpoint"] == "PENDING"


def test_feature_extraction_rejects_missing_gateway_record():
    with pytest.raises(ValueError, match="Gateway record not found"):
        extract_features("TXN_DOES_NOT_EXIST", data=load_data("data"))


def test_service_sends_exact_feature_contract_to_predictor(monkeypatch):
    captured = {}
    predictor_module = types.ModuleType("src.predictor")

    def fake_predict_delay_risk(features):
        captured.update(features)
        return {
            "applicable": True,
            "risk_score": 0.81,
            "risk_level": "HIGH",
            "predicted_delayed": True,
            "threshold_used": 0.2393,
            "model_version": "test",
            "reason": None,
        }

    predictor_module.predict_delay_risk = fake_predict_delay_risk
    monkeypatch.setitem(sys.modules, "src.predictor", predictor_module)

    result = analyze_transaction("TXN000042", data=load_data("data"))

    assert result["ml_prediction"]["applicable"] is True
    assert result["ml_prediction"]["risk_score"] == 0.81
    assert list(captured) == FEATURE_COLUMNS
