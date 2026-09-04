"""Phase 10 smoke tests for the trained XGBoost pipeline."""

import json
import sys
from pathlib import Path

import joblib
import pandas as pd

sys.path.insert(0, ".")

from config import MODEL_PATH  # noqa: E402
from src.ml_features import FEATURE_COLUMNS, TARGET_COLUMN  # noqa: E402


MODEL_FILE = Path(MODEL_PATH)
METRICS_FILE = Path("models/delay_model.metrics.json")
TRAINING_FILE = Path("data/ml_training_ready.csv")


def test_model_artifacts_exist():
    assert MODEL_FILE.is_file()
    assert METRICS_FILE.is_file()


def test_model_loads_and_predicts_probability():
    model = joblib.load(MODEL_FILE)
    table = pd.read_csv(TRAINING_FILE)
    sample = table[FEATURE_COLUMNS].head(3)

    probabilities = model.predict_proba(sample)[:, 1]

    assert len(probabilities) == len(sample)
    assert ((probabilities >= 0.0) & (probabilities <= 1.0)).all()


def test_metrics_report_contains_required_fields():
    metrics = json.loads(METRICS_FILE.read_text(encoding="utf-8"))

    assert metrics["model_type"] == "XGBClassifier"
    assert metrics["feature_columns"] == FEATURE_COLUMNS
    assert metrics["target_column"] == TARGET_COLUMN
    assert "default_threshold_metrics" in metrics
    assert "validation_selected_f2_threshold" in metrics
    assert "test_metrics_at_validation_threshold" in metrics
    assert "roc_auc" in metrics
    assert "pr_auc" in metrics


if __name__ == "__main__":
    test_model_artifacts_exist()
    test_model_loads_and_predicts_probability()
    test_metrics_report_contains_required_fields()
    print("ALL PHASE 10 SMOKE TESTS PASSED")
