"""Checkpoint-safe ML feature engineering.

This module is intentionally reusable by both training and inference code.
Keeping the feature contract here avoids train/serve skew: Phase 10 training
and Phase 11 prediction should use the same feature names and assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from config import (
    DATA_DIR,
    PREDICTION_CHECKPOINT_MINUTES,
    SETTLEMENT_SLA_MINUTES,
)
from src.loader import load_data
from src.validator import validate_transaction_id


FEATURE_COLUMNS = [
    "amount",
    "payment_method",
    "retry_count",
    "gateway_hour",
    "gateway_day_of_week",
    "gateway_is_weekend",
    "bank_observed_by_checkpoint",
    "bank_name_at_checkpoint",
    "bank_status_at_checkpoint",
    "bank_response_code_at_checkpoint",
    "bank_receive_lag_minutes",
    "bank_update_observed_by_checkpoint",
    "bank_age_minutes_at_checkpoint",
    "settlement_amount_at_checkpoint",
    "settlement_amount_delta_at_checkpoint",
]

TARGET_COLUMN = "is_delayed"

LEAKAGE_COLUMNS = {
    "transaction_id",
    "gateway_timestamp",
    "bank_received_at",
    "bank_updated_at",
    "ledger_timestamp",
    "final_settlement_at",
    "final_settlement_minutes",
    "total_delay",
    "delay_minutes",
    "bank_latency",
    "ledger_latency",
}


@dataclass(frozen=True)
class TrainingBuildResult:
    table: pd.DataFrame
    summary: dict[str, int | float]


def _as_columns(df: pd.DataFrame) -> pd.DataFrame:
    if "transaction_id" in df.columns:
        return df.reset_index(drop=True).copy()
    if df.index.name == "transaction_id":
        return df.reset_index()
    return df.copy()


def _latest_record(df: pd.DataFrame, sort_columns: list[str]) -> pd.DataFrame:
    existing_sort_columns = [col for col in sort_columns if col in df.columns]
    if existing_sort_columns:
        df = df.sort_values(
            ["transaction_id", *existing_sort_columns],
            na_position="last",
            kind="stable",
        )
    return df.drop_duplicates("transaction_id", keep="last")


def _minutes_between(later: pd.Series, earlier: pd.Series) -> pd.Series:
    return (later - earlier).dt.total_seconds() / 60.0


def load_feature_sources(
    data_dir: str = DATA_DIR,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and deduplicate the raw sources before feature construction."""
    loaded = load_data(data_dir)

    gateway = _latest_record(_as_columns(loaded["gateway"]), ["gateway_timestamp"])
    bank = _latest_record(
        _as_columns(loaded["bank"]), ["bank_received_at", "bank_updated_at"]
    )
    ledger = _latest_record(_as_columns(loaded["ledger"]), ["ledger_timestamp"])

    return gateway, bank, ledger


def _transaction_row(
    frame: pd.DataFrame,
    transaction_id: str,
    sort_columns: list[str],
) -> pd.Series | None:
    """Return the latest source row using the same ordering as training."""
    columns = _as_columns(frame)
    matches = columns.loc[columns["transaction_id"].eq(transaction_id)]
    if matches.empty:
        return None
    return _latest_record(matches, sort_columns).iloc[0]


def _timestamp_or_none(value: object) -> pd.Timestamp | None:
    if value is None or pd.isna(value):
        return None
    timestamp = pd.Timestamp(value)
    return None if pd.isna(timestamp) else timestamp


def _native_or_none(value: object) -> object | None:
    """Convert pandas missing/scalar values into predictor-safe Python values."""
    if value is None or pd.isna(value):
        return None
    try:
        return value.item()  # NumPy scalar
    except (AttributeError, ValueError):
        return value


def extract_features(
    transaction_id: str,
    data: dict[str, pd.DataFrame] | None = None,
    data_dir: str = DATA_DIR,
    checkpoint_minutes: int = PREDICTION_CHECKPOINT_MINUTES,
) -> dict[str, object | None]:
    """Build one checkpoint-safe inference row for ``predict_delay_risk``.

    Only evidence visible at ``gateway_timestamp + checkpoint_minutes`` is
    used. Ledger fields are deliberately excluded because final settlement is
    future information at prediction time.
    """
    clean_id = validate_transaction_id(transaction_id)
    if checkpoint_minutes <= 0:
        raise ValueError("checkpoint_minutes must be greater than zero")

    if data is None:
        data = load_data(data_dir)
    required_sources = {"gateway", "bank", "ledger"}
    missing_sources = required_sources - set(data)
    if missing_sources:
        raise ValueError(f"Missing feature data sources: {sorted(missing_sources)}")

    gateway = _transaction_row(
        data["gateway"], clean_id, ["gateway_timestamp"]
    )
    if gateway is None:
        raise ValueError(f"Gateway record not found for transaction '{clean_id}'.")

    gateway_timestamp = _timestamp_or_none(gateway.get("gateway_timestamp"))
    if gateway_timestamp is None:
        raise ValueError("gateway_timestamp is required for ML feature extraction")
    if str(gateway.get("gateway_status", "")).upper() != "SUCCESS":
        raise ValueError("ML feature extraction requires a successful gateway payment")

    checkpoint_at = gateway_timestamp + pd.to_timedelta(checkpoint_minutes, unit="m")
    bank = _transaction_row(
        data["bank"], clean_id, ["bank_received_at", "bank_updated_at"]
    )

    bank_received_at = None
    bank_updated_at = None
    bank_observed = False
    bank_update_observed = False
    bank_not_found_observed = False

    if bank is not None:
        bank_received_at = _timestamp_or_none(bank.get("bank_received_at"))
        bank_updated_at = _timestamp_or_none(bank.get("bank_updated_at"))
        bank_observed = (
            bank_received_at is not None and bank_received_at <= checkpoint_at
        )
        bank_update_observed = (
            bank_observed
            and bank_updated_at is not None
            and bank_updated_at <= checkpoint_at
        )
        bank_not_found_observed = (
            bank_observed
            and str(bank.get("bank_status", "")).upper() == "NOT_FOUND"
            and bank_updated_at is None
        )

    bank_name: object = "UNKNOWN"
    bank_status: object = "NOT_OBSERVED"
    bank_response_code: object = "NOT_OBSERVED"
    bank_receive_lag: float | None = None
    bank_age: float | None = None
    settlement_amount: object | None = None
    settlement_amount_delta: float | None = None

    if bank_observed and bank is not None and bank_received_at is not None:
        bank_name = _native_or_none(bank.get("bank_name")) or "UNKNOWN"
        bank_status = "PROCESSING"
        bank_response_code = "PENDING"
        bank_receive_lag = (
            bank_received_at - gateway_timestamp
        ).total_seconds() / 60.0

        observed_until = bank_updated_at if bank_update_observed else checkpoint_at
        bank_age = (observed_until - bank_received_at).total_seconds() / 60.0
        settlement_amount = _native_or_none(bank.get("settlement_amount"))

        gateway_amount = _native_or_none(gateway.get("amount"))
        if settlement_amount is not None and gateway_amount is not None:
            settlement_amount_delta = float(settlement_amount) - float(gateway_amount)

        if bank_update_observed or bank_not_found_observed:
            bank_status = str(bank.get("bank_status") or "UNKNOWN").upper()
            bank_response_code = _native_or_none(bank.get("bank_response_code"))
            if bank_response_code is None:
                bank_response_code = "UNKNOWN"

    gateway_hour = int(gateway_timestamp.hour)
    gateway_day_of_week = int(gateway_timestamp.dayofweek)
    features: dict[str, object | None] = {
        "amount": _native_or_none(gateway.get("amount")),
        "payment_method": _native_or_none(gateway.get("payment_method")),
        "retry_count": _native_or_none(gateway.get("retry_count")),
        "gateway_hour": gateway_hour,
        "gateway_day_of_week": gateway_day_of_week,
        "gateway_is_weekend": int(gateway_day_of_week in {5, 6}),
        "bank_observed_by_checkpoint": int(bank_observed),
        "bank_name_at_checkpoint": bank_name,
        "bank_status_at_checkpoint": bank_status,
        "bank_response_code_at_checkpoint": bank_response_code,
        "bank_receive_lag_minutes": bank_receive_lag,
        "bank_update_observed_by_checkpoint": int(bank_update_observed),
        "bank_age_minutes_at_checkpoint": bank_age,
        "settlement_amount_at_checkpoint": settlement_amount,
        "settlement_amount_delta_at_checkpoint": settlement_amount_delta,
    }

    if list(features) != FEATURE_COLUMNS:
        raise RuntimeError("Inference features do not match FEATURE_COLUMNS order")
    assert_no_feature_leakage(list(features))
    return features


def assert_no_feature_leakage(columns: list[str]) -> None:
    """Fail fast if a future-only or identifier column enters the feature set."""
    feature_columns = set(columns) - {TARGET_COLUMN}
    leaked = sorted(feature_columns & LEAKAGE_COLUMNS)
    if leaked:
        raise ValueError(f"Potential leakage columns in training features: {leaked}")


def validate_training_table(table: pd.DataFrame, include_ids: bool = False) -> None:
    """Validate the Phase 9 output contract before writing it to disk."""
    expected_columns = [*FEATURE_COLUMNS, TARGET_COLUMN]
    if include_ids:
        expected_columns = ["transaction_id", *expected_columns]

    if list(table.columns) != expected_columns:
        raise ValueError(
            "Training table columns do not match the ML feature contract. "
            f"Expected {expected_columns}, got {list(table.columns)}."
        )

    leakage_check_columns = list(table.columns)
    if include_ids:
        leakage_check_columns.remove("transaction_id")
    assert_no_feature_leakage(leakage_check_columns)

    target_values = set(table[TARGET_COLUMN].dropna().unique())
    if not target_values.issubset({0, 1}):
        raise ValueError(f"{TARGET_COLUMN} must be binary 0/1, got {target_values}.")

    if table.empty:
        raise ValueError("Training table is empty.")

    if table[TARGET_COLUMN].nunique() < 2:
        raise ValueError("Training table must contain both delayed and non-delayed rows.")

    empty_feature_columns = [
        column for column in FEATURE_COLUMNS if table[column].isna().all()
    ]
    if empty_feature_columns:
        raise ValueError(
            "Training feature columns cannot be entirely empty: "
            f"{empty_feature_columns}."
        )


def build_training_table(
    data_dir: str = DATA_DIR,
    checkpoint_minutes: int = PREDICTION_CHECKPOINT_MINUTES,
    sla_minutes: int = SETTLEMENT_SLA_MINUTES,
    include_ids: bool = False,
) -> TrainingBuildResult:
    """Build a leakage-safe supervised table for delay-risk modeling.

    Rows represent successful payments that were still unresolved at the
    prediction checkpoint and eventually received a posted ledger settlement.
    Future settlement information is used only for the target label.
    """
    gateway, bank, ledger = load_feature_sources(data_dir)

    initial_gateway_rows = len(gateway)
    demo_mask = gateway["transaction_id"].astype(str).str.startswith("TXN_DEMO_")
    gateway = gateway.loc[~demo_mask].copy()

    merged = gateway.merge(bank, on="transaction_id", how="left").merge(
        ledger, on="transaction_id", how="left"
    )

    checkpoint_at = merged["gateway_timestamp"] + pd.to_timedelta(
        checkpoint_minutes, unit="m"
    )

    ledger_posted = (
        merged["ledger_status"].eq("POSTED") & merged["ledger_timestamp"].notna()
    )
    final_settlement_at = merged["ledger_timestamp"].where(ledger_posted)
    final_settlement_minutes = _minutes_between(
        final_settlement_at, merged["gateway_timestamp"]
    )

    gateway_success = merged["gateway_status"].eq("SUCCESS")
    has_label = final_settlement_at.notna()
    open_at_checkpoint = final_settlement_at > checkpoint_at
    population_mask = gateway_success & has_label & open_at_checkpoint

    training = merged.loc[population_mask].copy()
    checkpoint_at = checkpoint_at.loc[population_mask]
    final_settlement_minutes = final_settlement_minutes.loc[population_mask]

    bank_observed = (
        training["bank_received_at"].notna()
        & (training["bank_received_at"] <= checkpoint_at)
    )
    bank_update_observed = (
        bank_observed
        & training["bank_updated_at"].notna()
        & (training["bank_updated_at"] <= checkpoint_at)
    )
    bank_not_found_observed = (
        bank_observed
        & training["bank_status"].eq("NOT_FOUND")
        & training["bank_updated_at"].isna()
    )

    bank_status_at_checkpoint = pd.Series(
        "NOT_OBSERVED", index=training.index, dtype="object"
    )
    bank_status_at_checkpoint.loc[bank_observed] = "PROCESSING"
    bank_status_at_checkpoint.loc[bank_update_observed] = training.loc[
        bank_update_observed, "bank_status"
    ]
    bank_status_at_checkpoint.loc[bank_not_found_observed] = "NOT_FOUND"

    bank_response_code_at_checkpoint = pd.Series(
        "NOT_OBSERVED", index=training.index, dtype="object"
    )
    bank_response_code_at_checkpoint.loc[bank_observed] = "PENDING"
    known_bank_response = bank_update_observed | bank_not_found_observed
    bank_response_code_at_checkpoint.loc[known_bank_response] = training.loc[
        known_bank_response, "bank_response_code"
    ].fillna("UNKNOWN")

    bank_observed_until = training["bank_updated_at"].where(
        bank_update_observed, checkpoint_at
    )
    bank_age_minutes = _minutes_between(
        bank_observed_until, training["bank_received_at"]
    ).where(bank_observed)

    features = pd.DataFrame(index=training.index)
    features["amount"] = training["amount"]
    features["payment_method"] = training["payment_method"]
    features["retry_count"] = training["retry_count"]
    features["gateway_hour"] = training["gateway_timestamp"].dt.hour
    features["gateway_day_of_week"] = training["gateway_timestamp"].dt.dayofweek
    features["gateway_is_weekend"] = (
        features["gateway_day_of_week"].isin([5, 6]).astype(int)
    )

    features["bank_observed_by_checkpoint"] = bank_observed.astype(int)
    features["bank_name_at_checkpoint"] = training["bank_name"].where(
        bank_observed, "UNKNOWN"
    )
    features["bank_status_at_checkpoint"] = bank_status_at_checkpoint
    features["bank_response_code_at_checkpoint"] = bank_response_code_at_checkpoint
    features["bank_receive_lag_minutes"] = _minutes_between(
        training["bank_received_at"], training["gateway_timestamp"]
    ).where(bank_observed)
    features["bank_update_observed_by_checkpoint"] = bank_update_observed.astype(int)
    features["bank_age_minutes_at_checkpoint"] = bank_age_minutes
    features["settlement_amount_at_checkpoint"] = training["settlement_amount"].where(
        bank_observed
    )
    features["settlement_amount_delta_at_checkpoint"] = (
        training["settlement_amount"] - training["amount"]
    ).where(bank_observed)

    features[TARGET_COLUMN] = (final_settlement_minutes > sla_minutes).astype(int)

    if include_ids:
        features.insert(0, "transaction_id", training["transaction_id"])

    output_columns = [*FEATURE_COLUMNS, TARGET_COLUMN]
    if include_ids:
        output_columns = ["transaction_id", *output_columns]
    table = features[output_columns]
    validate_training_table(table, include_ids=include_ids)

    delayed_rows = int(table[TARGET_COLUMN].sum())
    training_rows = len(table)
    summary: dict[str, int | float] = {
        "checkpoint_minutes": checkpoint_minutes,
        "sla_minutes": sla_minutes,
        "gateway_rows_read": initial_gateway_rows,
        "demo_rows_excluded": int(demo_mask.sum()),
        "gateway_success_rows": int(gateway_success.sum()),
        "rows_with_final_posted_ledger": int(has_label.sum()),
        "rows_settled_before_or_at_checkpoint": int(
            (gateway_success & has_label & ~open_at_checkpoint).sum()
        ),
        "rows_without_training_label": int((gateway_success & ~has_label).sum()),
        "training_rows": training_rows,
        "delayed_rows": delayed_rows,
        "not_delayed_rows": int((table[TARGET_COLUMN] == 0).sum()),
        "delayed_rate": round(delayed_rows / training_rows, 4),
    }

    return TrainingBuildResult(table=table, summary=summary)
