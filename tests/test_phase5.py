"""
Phase 5 tests — Transaction Tracer & Journey.

Covers: normal flow, missing bank, gateway failure, bank delay,
ledger delay, and non-existent transaction.
"""

import sys
import os
import pytest

# Ensure project root is on the path so `config` and `src.*` resolve.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.loader import load_data
from src.tracer import trace_transaction
from src.journey import build_journey


# ---------------------------------------------------------------------------
# Fixture: load data once for the entire module
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def data():
    """Load all three CSVs once for the test session."""
    return load_data("data")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _trace_and_journey(data, tx_id):
    """Shortcut: trace → journey in one call."""
    trace = trace_transaction(tx_id, data)
    journey = build_journey(trace)
    return trace, journey


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestTracer:
    """Tests for trace_transaction()."""

    def test_normal_transaction_found_in_all_sources(self, data):
        """TXN000002 (NORMAL) should exist in gateway, bank, and ledger."""
        trace = trace_transaction("TXN000002", data)

        assert trace["transaction_id"] == "TXN000002"
        assert trace["gateway"] is not None
        assert trace["bank"] is not None
        assert trace["ledger"] is not None

    def test_missing_bank_record(self, data):
        """TXN000020 (MISSING_BANK_RECORD) has no bank row."""
        trace = trace_transaction("TXN000020", data)

        assert trace["gateway"] is not None
        assert trace["bank"] is None
        assert trace["ledger"] is None  # ledger also missing per data

    def test_gateway_failure(self, data):
        """TXN000048 (GATEWAY_FAILURE) — gateway FAILED, bank has
        NOT_FOUND status, no ledger record."""
        trace = trace_transaction("TXN000048", data)

        assert trace["gateway"] is not None
        assert trace["gateway"]["gateway_status"] == "FAILED"
        assert trace["bank"] is not None
        assert trace["bank"]["bank_status"] == "NOT_FOUND"
        assert trace["ledger"] is None

    def test_nonexistent_transaction(self, data):
        """A made-up ID should return None for all three sources."""
        trace = trace_transaction("TXN_DOES_NOT_EXIST", data)

        assert trace["transaction_id"] == "TXN_DOES_NOT_EXIST"
        assert trace["gateway"] is None
        assert trace["bank"] is None
        assert trace["ledger"] is None

    def test_trace_returns_native_python_types(self, data):
        """Values in the trace dict must be native Python, not numpy/pandas."""
        trace = trace_transaction("TXN000002", data)

        gw = trace["gateway"]
        assert isinstance(gw["amount"], (int, float))
        # gateway_timestamp should be datetime, not pd.Timestamp
        from datetime import datetime
        assert isinstance(gw["gateway_timestamp"], datetime)


class TestJourney:
    """Tests for build_journey()."""

    def test_normal_all_hops_computed(self, data):
        """TXN000002 (NORMAL) should have all four elapsed times."""
        _, journey = _trace_and_journey(data, "TXN000002")

        assert journey["gateway_found"] is True
        assert journey["bank_found"] is True
        assert journey["ledger_found"] is True

        assert journey["gateway_to_bank_minutes"] is not None
        assert journey["bank_processing_minutes"] is not None
        assert journey["bank_to_ledger_minutes"] is not None
        assert journey["total_elapsed_minutes"] is not None

        # All hops should be non-negative for a normal transaction
        assert journey["gateway_to_bank_minutes"] >= 0
        assert journey["bank_processing_minutes"] >= 0
        assert journey["bank_to_ledger_minutes"] >= 0
        assert journey["total_elapsed_minutes"] >= 0

    def test_normal_hop_values_approximate(self, data):
        """TXN000002 hops should roughly match demo_transactions.csv
        (gateway_latency ≈ 0.98, bank_latency ≈ 6.92, ledger_latency ≈ 1.04).
        """
        _, journey = _trace_and_journey(data, "TXN000002")

        assert abs(journey["gateway_to_bank_minutes"] - 0.98) < 0.1
        assert abs(journey["bank_processing_minutes"] - 6.92) < 0.1
        assert abs(journey["bank_to_ledger_minutes"] - 1.04) < 0.1

    def test_missing_bank_hops_are_none(self, data):
        """TXN000020 (MISSING_BANK_RECORD) — all hops involving bank
        should be None.
        """
        _, journey = _trace_and_journey(data, "TXN000020")

        assert journey["gateway_found"] is True
        assert journey["bank_found"] is False
        assert journey["ledger_found"] is False

        assert journey["gateway_to_bank_minutes"] is None
        assert journey["bank_processing_minutes"] is None
        assert journey["bank_to_ledger_minutes"] is None
        assert journey["total_elapsed_minutes"] is None

    def test_gateway_failure_partial_hops(self, data):
        """TXN000048 (GATEWAY_FAILURE) — gateway FAILED, bank has
        NOT_FOUND status, no ledger. Hop 1 computable, Hop 3 and
        total should be None (no ledger).
        """
        _, journey = _trace_and_journey(data, "TXN000048")

        assert journey["gateway_found"] is True
        assert journey["bank_found"] is True
        assert journey["ledger_found"] is False

        # Hop 1 (gateway → bank) should be computable
        assert journey["gateway_to_bank_minutes"] is not None
        # Hop 3 (bank → ledger) should be None — no ledger
        assert journey["bank_to_ledger_minutes"] is None
        # Total should be None — no ledger endpoint
        assert journey["total_elapsed_minutes"] is None

    def test_bank_delay_large_processing(self, data):
        """TXN000001 (BANK_DELAY) — bank_processing should be ~29.15 min."""
        _, journey = _trace_and_journey(data, "TXN000001")

        assert journey["bank_processing_minutes"] is not None
        assert journey["bank_processing_minutes"] > 25  # substantially delayed

    def test_ledger_delay_large_hop3(self, data):
        """TXN000070 (LEDGER_DELAY) — bank_to_ledger should be ~11.76 min."""
        _, journey = _trace_and_journey(data, "TXN000070")

        assert journey["bank_to_ledger_minutes"] is not None
        assert journey["bank_to_ledger_minutes"] > 10  # substantially delayed

    def test_nonexistent_journey_all_none(self, data):
        """Non-existent transaction — all timestamps None, all hops None."""
        _, journey = _trace_and_journey(data, "TXN_DOES_NOT_EXIST")

        assert journey["gateway_found"] is False
        assert journey["bank_found"] is False
        assert journey["ledger_found"] is False

        assert journey["gateway_timestamp"] is None
        assert journey["bank_received_at"] is None
        assert journey["bank_updated_at"] is None
        assert journey["ledger_timestamp"] is None

        assert journey["gateway_to_bank_minutes"] is None
        assert journey["bank_processing_minutes"] is None
        assert journey["bank_to_ledger_minutes"] is None
        assert journey["total_elapsed_minutes"] is None
