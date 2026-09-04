"""
Phase 8 tests — Exception Handling & Evidence Confidence.

Covers all 8 demo scenarios plus a non-existent transaction.
Validates exception flags and confidence levels.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.loader import load_data
from src.tracer import trace_transaction
from src.journey import build_journey
from src.rules import apply_rules
from src.exceptions import evaluate_exceptions, VALID_CONFIDENCE_LEVELS, VALID_EXCEPTION_FLAGS


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def data():
    return load_data("data")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _full_pipeline(data, tx_id):
    """trace → journey → rules → exceptions."""
    trace = trace_transaction(tx_id, data)
    journey = build_journey(trace)
    rules_result = apply_rules(journey, trace)
    exc_result = evaluate_exceptions(journey, trace, rules_result)
    return exc_result, rules_result, journey, trace


# ---------------------------------------------------------------------------
# Confidence tests
# ---------------------------------------------------------------------------

class TestEvidenceConfidence:

    def test_normal_high_confidence(self, data):
        """TXN000002 (NORMAL) — all records present, no anomalies → HIGH."""
        exc, _, _, _ = _full_pipeline(data, "TXN000002")
        assert exc["evidence_confidence"] == "HIGH"

    def test_missing_bank_low_confidence(self, data):
        """TXN000020 (MISSING_BANK) — core record missing → LOW."""
        exc, _, _, _ = _full_pipeline(data, "TXN000020")
        assert exc["evidence_confidence"] == "LOW"

    def test_gateway_failure_low_confidence(self, data):
        """TXN000048 (GATEWAY_FAILURE) — gateway failed, no downstream → LOW."""
        exc, _, _, _ = _full_pipeline(data, "TXN000048")
        assert exc["evidence_confidence"] == "LOW"

    def test_amount_mismatch_medium_confidence(self, data):
        """TXN000035 (AMOUNT_MISMATCH) — all records present but amounts
        disagree → MEDIUM."""
        exc, _, _, _ = _full_pipeline(data, "TXN000035")
        assert exc["evidence_confidence"] == "MEDIUM"

    def test_nonexistent_low_confidence(self, data):
        """Non-existent ID — no records at all → LOW."""
        exc, _, _, _ = _full_pipeline(data, "TXN_DOES_NOT_EXIST")
        assert exc["evidence_confidence"] == "LOW"

    def test_confidence_always_valid(self, data):
        """Confidence must be one of HIGH/MEDIUM/LOW for all demo txns."""
        for tx_id in ["TXN000001", "TXN000002", "TXN000020", "TXN000035",
                       "TXN000042", "TXN000048", "TXN000065", "TXN000070"]:
            exc, _, _, _ = _full_pipeline(data, tx_id)
            assert exc["evidence_confidence"] in VALID_CONFIDENCE_LEVELS, (
                f"{tx_id}: got '{exc['evidence_confidence']}'"
            )


# ---------------------------------------------------------------------------
# Exception flag tests
# ---------------------------------------------------------------------------

class TestExceptionFlags:

    def test_normal_no_critical_exceptions(self, data):
        """TXN000002 (NORMAL) — should have no missing-record exceptions."""
        exc, _, _, _ = _full_pipeline(data, "TXN000002")
        missing_flags = {"GATEWAY_RECORD_MISSING", "BANK_RECORD_MISSING",
                         "LEDGER_RECORD_MISSING"}
        assert not (set(exc["exceptions"]) & missing_flags)

    def test_missing_bank_has_flag(self, data):
        """TXN000020 (MISSING_BANK) — must include BANK_RECORD_MISSING."""
        exc, _, _, _ = _full_pipeline(data, "TXN000020")
        assert "BANK_RECORD_MISSING" in exc["exceptions"]

    def test_gateway_failure_has_flag(self, data):
        """TXN000048 (GATEWAY_FAILURE) — must include GATEWAY_FAILURE."""
        exc, _, _, _ = _full_pipeline(data, "TXN000048")
        assert "GATEWAY_FAILURE" in exc["exceptions"]

    def test_amount_mismatch_has_flag(self, data):
        """TXN000035 — must include AMOUNT_MISMATCH."""
        exc, _, _, _ = _full_pipeline(data, "TXN000035")
        assert "AMOUNT_MISMATCH" in exc["exceptions"]

    def test_duplicate_retry_has_flag(self, data):
        """TXN000065 (DUPLICATE_RETRY, retry_count=2) — must include
        DUPLICATE_RETRY_SUSPECTED."""
        exc, _, _, _ = _full_pipeline(data, "TXN000065")
        assert "DUPLICATE_RETRY_SUSPECTED" in exc["exceptions"]

    def test_bank_delay_has_processing_flag(self, data):
        """TXN000001 (BANK_DELAY, bank_processing=29.15 > 15) — must
        include BANK_PROCESSING_DELAY."""
        exc, _, _, _ = _full_pipeline(data, "TXN000001")
        assert "BANK_PROCESSING_DELAY" in exc["exceptions"]

    def test_ledger_delay_has_posting_flag(self, data):
        """TXN000070 (LEDGER_DELAY, bank_to_ledger=11.76 > 5) — must
        include LEDGER_POSTING_DELAY."""
        exc, _, _, _ = _full_pipeline(data, "TXN000070")
        assert "LEDGER_POSTING_DELAY" in exc["exceptions"]

    def test_nonexistent_all_missing(self, data):
        """Non-existent ID — all three RECORD_MISSING flags."""
        exc, _, _, _ = _full_pipeline(data, "TXN_DOES_NOT_EXIST")
        assert "GATEWAY_RECORD_MISSING" in exc["exceptions"]
        assert "BANK_RECORD_MISSING" in exc["exceptions"]
        assert "LEDGER_RECORD_MISSING" in exc["exceptions"]

    def test_exceptions_always_sorted(self, data):
        """Exceptions list must be sorted for deterministic output."""
        for tx_id in ["TXN000001", "TXN000002", "TXN000020", "TXN000035",
                       "TXN000048", "TXN000065", "TXN000070"]:
            exc, _, _, _ = _full_pipeline(data, tx_id)
            assert exc["exceptions"] == sorted(exc["exceptions"])

    def test_exceptions_all_valid_flags(self, data):
        """Every exception flag must be in the valid set."""
        for tx_id in ["TXN000001", "TXN000002", "TXN000020", "TXN000035",
                       "TXN000042", "TXN000048", "TXN000065", "TXN000070"]:
            exc, _, _, _ = _full_pipeline(data, tx_id)
            for flag in exc["exceptions"]:
                assert flag in VALID_EXCEPTION_FLAGS, (
                    f"{tx_id}: unknown flag '{flag}'"
                )


# ---------------------------------------------------------------------------
# Overlap mapping tests (BUILD_PLAN requirement)
# ---------------------------------------------------------------------------

class TestOverlapMapping:
    """Verify that status + confidence combinations are correct
    for key overlap scenarios."""

    def test_missing_bank_unresolved_low(self, data):
        """Missing bank → UNRESOLVED + LOW confidence."""
        exc, rules, _, _ = _full_pipeline(data, "TXN000020")
        assert rules["status"] == "UNRESOLVED"
        assert exc["evidence_confidence"] == "LOW"

    def test_settled_with_mismatch_medium(self, data):
        """Amount mismatch but settled → SETTLED + MEDIUM confidence."""
        exc, rules, _, _ = _full_pipeline(data, "TXN000035")
        assert rules["status"] == "SETTLED"
        assert exc["evidence_confidence"] == "MEDIUM"

    def test_normal_settled_high(self, data):
        """Normal settlement → SETTLED + HIGH confidence."""
        exc, rules, _, _ = _full_pipeline(data, "TXN000002")
        assert rules["status"] == "SETTLED"
        assert exc["evidence_confidence"] == "HIGH"

    def test_gateway_failure_failed_low(self, data):
        """Gateway failure → FAILED + LOW confidence."""
        exc, rules, _, _ = _full_pipeline(data, "TXN000048")
        assert rules["status"] == "FAILED"
        assert exc["evidence_confidence"] == "LOW"
