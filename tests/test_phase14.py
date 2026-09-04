"""
Phase 14 Integration Tests — Service Orchestration (src/service.py).

Validates:
- End-to-end analyze_transaction() contract for normal, delayed, and missing records.
- ML prediction failure isolation (graceful degradation when ML fails).
- ETA estimation failure isolation (graceful degradation when ETA fails).
- Input validation & invalid ID error handling.
"""

import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.loader import load_data
from src.service import analyze_transaction


@pytest.fixture(scope="module")
def data():
    return load_data("data")


def test_analyze_transaction_normal_settled(data):
    """TXN000002 (NORMAL) should return SETTLED with HIGH confidence."""
    res = analyze_transaction("TXN000002", data=data)

    assert res["transaction_id"] == "TXN000002"
    assert res["status"] == "SETTLED"
    assert res["evidence_confidence"] == "HIGH"
    assert "recommendation" in res
    assert "action" in res["recommendation"]
    assert res["ml_prediction"]["applicable"] is False  # Already settled
    assert res["trace"]["gateway"] is not None
    assert res["trace"]["bank"] is not None
    assert res["trace"]["ledger"] is not None


def test_analyze_transaction_missing_bank(data):
    """TXN000020 (MISSING_BANK) should return UNRESOLVED with LOW confidence."""
    res = analyze_transaction("TXN000020", data=data)

    assert res["transaction_id"] == "TXN000020"
    assert res["status"] == "UNRESOLVED"
    assert res["evidence_confidence"] == "LOW"
    assert "BANK_RECORD_MISSING" in res["exceptions"]
    assert res["trace"]["bank"] is None


def test_ml_failure_isolation(data):
    """Forcing an exception in ML predictor should not break analyze_transaction."""
    with patch("src.predictor.predict_delay_risk", side_effect=RuntimeError("Simulated Model Failure")):
        # Use an in-progress transaction (TXN000042)
        res = analyze_transaction("TXN000042", data=data)

        # Main orchestration must succeed despite ML failure
        assert res["transaction_id"] == "TXN000042"
        assert res["ml_prediction"]["applicable"] is False
        assert "ML prediction unavailable" in res["ml_prediction"]["reason"]


def test_eta_failure_isolation(data):
    """Forcing an exception in ETA estimator should not break analyze_transaction."""
    with patch("src.estimator.estimate_additional_delay", side_effect=RuntimeError("Simulated ETA Failure")):
        res = analyze_transaction("TXN000001", data=data)

        # Main orchestration must succeed despite ETA failure
        assert res["transaction_id"] == "TXN000001"
        assert res["eta_estimation"]["applicable"] is False
        assert "ETA estimation unavailable" in res["eta_estimation"]["reason"]


def test_invalid_transaction_id():
    """Invalid transaction ID format should raise ValueError."""
    with pytest.raises(ValueError):
        analyze_transaction("INVALID;DROP TABLE--")
