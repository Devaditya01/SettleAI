"""Phase 11 smoke tests for the prediction service."""

import sys

import pandas as pd

sys.path.insert(0, ".")

from src.ml_features import FEATURE_COLUMNS  # noqa: E402
from src.predictor import predict_delay_risk  # noqa: E402


def _sample_feature_dict() -> dict:
    table = pd.read_csv("data/ml_training_ready.csv")
    return table[FEATURE_COLUMNS].iloc[0].to_dict()


def test_predict_delay_risk_returns_contract():
    prediction = predict_delay_risk(_sample_feature_dict())

    assert prediction["applicable"] is True
    assert isinstance(prediction["risk_score"], float)
    assert 0.0 <= prediction["risk_score"] <= 1.0
    assert prediction["risk_level"] in {"LOW", "MEDIUM", "HIGH"}
    assert isinstance(prediction["predicted_delayed"], bool)
    assert isinstance(prediction["threshold_used"], float)
    assert prediction["reason"] is None


def test_predict_delay_risk_rejects_missing_features():
    feature_dict = _sample_feature_dict()
    feature_dict.pop(FEATURE_COLUMNS[0])

    try:
        predict_delay_risk(feature_dict)
    except ValueError as exc:
        assert "Missing required model features" in str(exc)
    else:
        raise AssertionError("predict_delay_risk should reject missing features")


if __name__ == "__main__":
    test_predict_delay_risk_returns_contract()
    test_predict_delay_risk_rejects_missing_features()
    print("ALL PHASE 11 SMOKE TESTS PASSED")
