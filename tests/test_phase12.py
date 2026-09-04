"""Phase 12 smoke tests for the historical ETA estimator."""

import sys

sys.path.insert(0, ".")

from src.estimator import estimate_additional_delay  # noqa: E402


def test_exact_segment_estimate_returns_contract():
    estimate = estimate_additional_delay("BANK_B", "UPI")

    assert estimate["applicable"] is True
    assert estimate["basis"] == "bank_and_payment_method"
    assert estimate["sample_size"] >= 10
    assert estimate["confidence"] in {"MEDIUM", "HIGH"}
    assert estimate["estimated_additional_delay_minutes"] > 0
    assert estimate["median_final_settlement_minutes"] > 30
    assert estimate["reason"] is None


def test_estimate_falls_back_when_exact_segment_is_missing():
    estimate = estimate_additional_delay("BANK_UNKNOWN", "UPI")

    assert estimate["applicable"] is True
    assert estimate["basis"] in {"payment_method", "global"}
    assert estimate["sample_size"] > 0
    assert estimate["estimated_additional_delay_minutes"] > 0


def test_estimate_requires_a_segment_hint():
    estimate = estimate_additional_delay(None, None)

    assert estimate["applicable"] is False
    assert estimate["estimated_additional_delay_minutes"] is None
    assert estimate["confidence"] == "LOW"


if __name__ == "__main__":
    test_exact_segment_estimate_returns_contract()
    test_estimate_falls_back_when_exact_segment_is_missing()
    test_estimate_requires_a_segment_hint()
    print("ALL PHASE 12 SMOKE TESTS PASSED")
