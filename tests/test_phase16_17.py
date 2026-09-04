"""
Phase 16 & 17 tests — Streamlit UI & Recommendation Integration.

Validates:
- Data loader & search filtering by date.
- Recommendation mapping for all valid root causes.
- End-to-end trace to UI data conversion.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.loader import load_data
from src.tracer import trace_transaction
from src.journey import build_journey
from src.rules import apply_rules, VALID_ROOT_CAUSES
from src.exceptions import evaluate_exceptions
from src.recommendations import get_recommendation, RECOMMENDATION_MAP


@pytest.fixture(scope="module")
def data():
    return load_data("data")


def test_recommendation_coverage_all_root_causes():
    """Ensure every deterministic root cause has an actionable recommendation."""
    for cause in VALID_ROOT_CAUSES:
        rec = get_recommendation(cause)
        assert "action" in rec
        assert "title" in rec
        assert "description" in rec
        assert rec["action"] != ""


def test_date_search_filtering(data):
    """Test filtering Gateway DataFrame by payment date."""
    gw_df = data["gateway"]
    assert "gateway_timestamp" in gw_df.columns
    
    dates = gw_df["gateway_timestamp"].dropna().dt.strftime("%Y-%m-%d").unique()
    assert len(dates) > 0
    
    sample_date = dates[0]
    filtered = gw_df[gw_df["gateway_timestamp"].dt.strftime("%Y-%m-%d") == sample_date]
    assert len(filtered) > 0


def test_full_pipeline_ui_data_payload(data):
    """Verify that full pipeline produces valid UI payload for TXN000002."""
    trace = trace_transaction("TXN000002", data)
    journey = build_journey(trace)
    rules = apply_rules(journey, trace)
    exc = evaluate_exceptions(journey, trace, rules)
    rec = get_recommendation(rules["root_cause"])

    assert rules["status"] in ["SETTLED", "FAILED", "PROCESSING", "AT_RISK", "DELAYED", "UNRESOLVED"]
    assert exc["evidence_confidence"] in ["HIGH", "MEDIUM", "LOW"]
    assert rec["action"] != ""
