"""Phase 9 smoke tests for the ML training table."""

import sys

sys.path.insert(0, ".")

from src.ml_features import (  # noqa: E402
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_training_table,
)


def test_training_table_contract():
    result = build_training_table("data")
    table = result.table

    assert list(table.columns) == [*FEATURE_COLUMNS, TARGET_COLUMN]
    assert len(table) > 0
    assert set(table[TARGET_COLUMN].unique()) == {0, 1}
    assert "transaction_id" not in table.columns


def test_training_table_avoids_obvious_leakage_columns():
    result = build_training_table("data")
    columns = set(result.table.columns)

    forbidden = {
        "gateway_timestamp",
        "bank_received_at",
        "bank_updated_at",
        "ledger_timestamp",
        "final_settlement_at",
        "final_settlement_minutes",
        "delay_minutes",
        "total_delay",
        "bank_latency",
        "ledger_latency",
    }

    assert not (columns & forbidden)


if __name__ == "__main__":
    test_training_table_contract()
    test_training_table_avoids_obvious_leakage_columns()
    print("ALL PHASE 9 SMOKE TESTS PASSED")
