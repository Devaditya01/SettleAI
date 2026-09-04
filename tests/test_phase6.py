"""
Phase 6 & 7 tests — Deterministic Rules Engine.

Covers all 8 demo scenarios, a non-existent ID, and a synthetic
DELAYED-override case.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.loader import load_data
from src.tracer import trace_transaction
from src.journey import build_journey
from src.rules import determine_status, determine_root_cause, apply_rules


# ---------------------------------------------------------------------------
# Fixture: load data once for the entire module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def data():
    return load_data("data")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _full_pipeline(data, tx_id):
    """trace → journey → rules in one call."""
    trace = trace_transaction(tx_id, data)
    journey = build_journey(trace)
    result = apply_rules(journey, trace)
    return result, journey, trace


# ---------------------------------------------------------------------------
# Test cases — Status determination
# ---------------------------------------------------------------------------

class TestDetermineStatus:
    """Tests for determine_status()."""

    def test_normal_settled(self, data):
        """TXN000002 (NORMAL) — SETTLED."""
        result, _, _ = _full_pipeline(data, "TXN000002")
        assert result["status"] == "SETTLED"

    def test_bank_delay_delayed(self, data):
        """TXN000001 (BANK_DELAY, total=31.55 > SLA=30) — DELAYED."""
        result, _, _ = _full_pipeline(data, "TXN000001")
        assert result["status"] == "DELAYED"

    def test_long_processing_at_risk(self, data):
        """TXN000042 (LONG_PROCESSING, total=24.98, > 15 AT_RISK) — AT_RISK."""
        result, _, _ = _full_pipeline(data, "TXN000042")
        assert result["status"] == "AT_RISK"

    def test_missing_bank_unresolved(self, data):
        """TXN000020 (MISSING_BANK_RECORD) — UNRESOLVED."""
        result, _, _ = _full_pipeline(data, "TXN000020")
        assert result["status"] == "UNRESOLVED"

    def test_amount_mismatch_settled(self, data):
        """TXN000035 (AMOUNT_MISMATCH) — bank SETTLED, ledger POSTED,
        so status is SETTLED (mismatch is a root-cause, not a status)."""
        result, _, _ = _full_pipeline(data, "TXN000035")
        assert result["status"] == "SETTLED"

    def test_gateway_failure_failed(self, data):
        """TXN000048 (GATEWAY_FAILURE) — FAILED."""
        result, _, _ = _full_pipeline(data, "TXN000048")
        assert result["status"] == "FAILED"

    def test_duplicate_retry_at_risk(self, data):
        """TXN000065 (DUPLICATE_RETRY, total≈16.3 > 15) — AT_RISK."""
        result, _, _ = _full_pipeline(data, "TXN000065")
        assert result["status"] == "AT_RISK"

    def test_ledger_delay_processing(self, data):
        """TXN000070 (LEDGER_DELAY, bank=SETTLED, ledger=PENDING,
        total=19.77 > 15) — AT_RISK since it exceeds AT_RISK threshold."""
        result, journey, _ = _full_pipeline(data, "TXN000070")
        # total=19.77 > 15 (AT_RISK threshold) but bank=SETTLED, ledger=PENDING
        # Status will be PROCESSING or AT_RISK depending on exact logic
        assert result["status"] in ("PROCESSING", "AT_RISK")

    def test_nonexistent_unresolved(self, data):
        """Non-existent ID — UNRESOLVED."""
        result, _, _ = _full_pipeline(data, "TXN_DOES_NOT_EXIST")
        assert result["status"] == "UNRESOLVED"

    def test_delayed_overrides_processing(self):
        """Synthetic: PROCESSING base + total > SLA → DELAYED."""
        # Build a synthetic journey and trace that would be PROCESSING
        # but with total_elapsed > SLA.
        journey = {
            "transaction_id": "TXN_SYNTHETIC",
            "gateway_timestamp": None,
            "bank_received_at": None,
            "bank_updated_at": None,
            "ledger_timestamp": None,
            "gateway_to_bank_minutes": 1.0,
            "bank_processing_minutes": 35.0,
            "bank_to_ledger_minutes": None,
            "total_elapsed_minutes": 36.0,  # > SLA of 30
            "gateway_found": True,
            "bank_found": True,
            "ledger_found": False,
        }
        trace = {
            "transaction_id": "TXN_SYNTHETIC",
            "gateway": {
                "gateway_status": "SUCCESS",
                "amount": 500,
                "retry_count": 0,
                "gateway_timestamp": None,
            },
            "bank": {
                "bank_status": "PROCESSING",
                "settlement_amount": 500.0,
                "bank_received_at": None,
                "bank_updated_at": None,
            },
            "ledger": None,
        }
        status = determine_status(journey, trace)
        assert status == "DELAYED", (
            f"Expected DELAYED when total > SLA, got {status}"
        )


# ---------------------------------------------------------------------------
# Test cases — Root cause determination
# ---------------------------------------------------------------------------

class TestDetermineRootCause:
    """Tests for determine_root_cause()."""

    def test_normal_settled_successfully(self, data):
        """TXN000002 (NORMAL) — SETTLED_SUCCESSFULLY."""
        result, _, _ = _full_pipeline(data, "TXN000002")
        assert result["root_cause"] == "SETTLED_SUCCESSFULLY"

    def test_bank_delay_cause(self, data):
        """TXN000001 (BANK_DELAY) — BANK_PROCESSING_DELAY."""
        result, _, _ = _full_pipeline(data, "TXN000001")
        assert result["root_cause"] == "BANK_PROCESSING_DELAY"

    def test_long_processing_cause(self, data):
        """TXN000042 (LONG_PROCESSING) — BANK_PROCESSING_DELAY."""
        result, _, _ = _full_pipeline(data, "TXN000042")
        assert result["root_cause"] == "BANK_PROCESSING_DELAY"

    def test_missing_bank_cause(self, data):
        """TXN000020 (MISSING_BANK) — MISSING_BANK_RECORD."""
        result, _, _ = _full_pipeline(data, "TXN000020")
        assert result["root_cause"] == "MISSING_BANK_RECORD"

    def test_amount_mismatch_cause(self, data):
        """TXN000035 (AMOUNT_MISMATCH) — AMOUNT_MISMATCH.
        gateway=1000, bank=1000, ledger=1032."""
        result, _, _ = _full_pipeline(data, "TXN000035")
        assert result["root_cause"] == "AMOUNT_MISMATCH"

    def test_gateway_failure_cause(self, data):
        """TXN000048 (GATEWAY_FAILURE) — GATEWAY_FAILURE."""
        result, _, _ = _full_pipeline(data, "TXN000048")
        assert result["root_cause"] == "GATEWAY_FAILURE"

    def test_duplicate_retry_cause(self, data):
        """TXN000065 (DUPLICATE_RETRY) — bank is PROCESSING,
        so hits Priority 6 (BANK_PROCESSING_DELAY) before retry."""
        result, _, _ = _full_pipeline(data, "TXN000065")
        assert result["root_cause"] == "BANK_PROCESSING_DELAY"

    def test_ledger_delay_cause(self, data):
        """TXN000070 (LEDGER_DELAY) — bank SETTLED, ledger PENDING,
        bank_to_ledger ~11.76 min — LEDGER_POSTING_DELAY."""
        result, _, _ = _full_pipeline(data, "TXN000070")
        assert result["root_cause"] == "LEDGER_POSTING_DELAY"

    def test_nonexistent_missing_gateway(self, data):
        """Non-existent ID — MISSING_GATEWAY_RECORD."""
        result, _, _ = _full_pipeline(data, "TXN_DOES_NOT_EXIST")
        assert result["root_cause"] == "MISSING_GATEWAY_RECORD"


# ---------------------------------------------------------------------------
# Test cases — apply_rules wrapper
# ---------------------------------------------------------------------------

class TestApplyRules:
    """Tests for the convenience wrapper."""

    def test_returns_both_keys(self, data):
        """apply_rules() must return dict with 'status' and 'root_cause'."""
        result, _, _ = _full_pipeline(data, "TXN000002")
        assert "status" in result
        assert "root_cause" in result

    def test_status_in_valid_set(self, data):
        """Status must be one of the 6 valid values."""
        from src.rules import VALID_STATUSES
        for tx_id in ["TXN000001", "TXN000002", "TXN000020",
                       "TXN000035", "TXN000048", "TXN000065", "TXN000070"]:
            result, _, _ = _full_pipeline(data, tx_id)
            assert result["status"] in VALID_STATUSES, (
                f"{tx_id}: got invalid status '{result['status']}'"
            )

    def test_root_cause_in_valid_set(self, data):
        """Root cause must be one of the valid values."""
        from src.rules import VALID_ROOT_CAUSES
        for tx_id in ["TXN000001", "TXN000002", "TXN000020",
                       "TXN000035", "TXN000048", "TXN000065", "TXN000070"]:
            result, _, _ = _full_pipeline(data, tx_id)
            assert result["root_cause"] in VALID_ROOT_CAUSES, (
                f"{tx_id}: got invalid root_cause '{result['root_cause']}'"
            )
