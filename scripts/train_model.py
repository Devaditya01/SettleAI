"""Phase 10: train the XGBoost delay-risk model.

This script consumes data/ml_training_ready.csv from Phase 9, trains a
reproducible sklearn Pipeline with preprocessing + XGBoost, prints the core
classification metrics, and saves both the model artifact and evaluation
metadata.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import MODEL_PATH, RANDOM_SEED  # noqa: E402
from src.ml_features import FEATURE_COLUMNS, TARGET_COLUMN, validate_training_table  # noqa: E402


DEFAULT_TRAINING_PATH = ROOT_DIR / "data" / "ml_training_ready.csv"
DEFAULT_MODEL_PATH = ROOT_DIR / MODEL_PATH
DEFAULT_METRICS_PATH = ROOT_DIR / "models" / "delay_model.metrics.json"
DEFAULT_TEST_SIZE = 0.20
DEFAULT_VALIDATION_SIZE = 0.20


def repo_display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return str(resolved)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the delay-risk XGBoost model.")
    parser.add_argument("--training-data", default=str(DEFAULT_TRAINING_PATH))
    parser.add_argument("--model-output", default=str(DEFAULT_MODEL_PATH))
    parser.add_argument("--metrics-output", default=str(DEFAULT_METRICS_PATH))
    parser.add_argument("--test-size", type=float, default=DEFAULT_TEST_SIZE)
    parser.add_argument("--validation-size", type=float, default=DEFAULT_VALIDATION_SIZE)
    return parser.parse_args()


def load_training_data(path: Path) -> tuple[pd.DataFrame, pd.Series]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Training data not found: {path}. Run scripts/build_training_data.py first."
        )

    table = pd.read_csv(path)
    validate_training_table(table)

    x = table[FEATURE_COLUMNS]
    y = table[TARGET_COLUMN].astype(int)
    return x, y


def split_columns(x: pd.DataFrame) -> tuple[list[str], list[str]]:
    categorical_columns = [
        "payment_method",
        "bank_name_at_checkpoint",
        "bank_status_at_checkpoint",
        "bank_response_code_at_checkpoint",
    ]
    categorical_columns = [c for c in categorical_columns if c in x.columns]
    numeric_columns = [column for column in x.columns if column not in categorical_columns]
    return numeric_columns, categorical_columns


def build_pipeline(x_train: pd.DataFrame, y_train: pd.Series) -> Pipeline:
    numeric_columns, categorical_columns = split_columns(x_train)
    negative_count = int((y_train == 0).sum())
    positive_count = int((y_train == 1).sum())
    scale_pos_weight = negative_count / positive_count

    numeric_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median"))]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="constant", fill_value="UNKNOWN")),
            ("encoder", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_transformer, numeric_columns),
            ("categorical", categorical_transformer, categorical_columns),
        ]
    )

    classifier = XGBClassifier(
        objective="binary:logistic",
        eval_metric="logloss",
        n_estimators=250,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        min_child_weight=3,
        reg_lambda=1.0,
        scale_pos_weight=scale_pos_weight,
        random_state=RANDOM_SEED,
        n_jobs=-1,
        tree_method="hist",
    )

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )


def choose_f2_threshold(y_true: pd.Series, probabilities: np.ndarray) -> dict[str, float]:
    precision, recall, thresholds = precision_recall_curve(y_true, probabilities)
    candidates = []

    for index, threshold in enumerate(thresholds):
        p = precision[index]
        r = recall[index]
        denominator = (4 * p) + r
        f2 = 0.0 if denominator == 0 else (5 * p * r) / denominator
        candidates.append((float(f2), float(threshold), float(p), float(r)))

    best_f2, best_threshold, best_precision, best_recall = max(
        candidates, key=lambda item: (item[0], item[3], item[2])
    )
    return {
        "threshold": round(best_threshold, 4),
        "precision": round(best_precision, 4),
        "recall": round(best_recall, 4),
        "f2": round(best_f2, 4),
    }


def evaluate_predictions(
    y_true: pd.Series,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    predictions = (probabilities >= threshold).astype(int)
    labels = [0, 1]
    cm = confusion_matrix(y_true, predictions, labels=labels)

    return {
        "threshold": threshold,
        "accuracy": round(accuracy_score(y_true, predictions), 4),
        "precision_delayed": round(
            precision_score(y_true, predictions, pos_label=1, zero_division=0), 4
        ),
        "recall_delayed": round(
            recall_score(y_true, predictions, pos_label=1, zero_division=0), 4
        ),
        "f1_delayed": round(
            f1_score(y_true, predictions, pos_label=1, zero_division=0), 4
        ),
        "confusion_matrix": {
            "labels": labels,
            "matrix": cm.tolist(),
            "tn": int(cm[0][0]),
            "fp": int(cm[0][1]),
            "fn": int(cm[1][0]),
            "tp": int(cm[1][1]),
        },
    }


def train_model(
    training_data_path: Path = DEFAULT_TRAINING_PATH,
    model_output_path: Path = DEFAULT_MODEL_PATH,
    metrics_output_path: Path = DEFAULT_METRICS_PATH,
    test_size: float = DEFAULT_TEST_SIZE,
    validation_size: float = DEFAULT_VALIDATION_SIZE,
) -> dict[str, object]:
    x, y = load_training_data(training_data_path)

    x_train_val, x_test, y_train_val, y_test = train_test_split(
        x,
        y,
        test_size=test_size,
        random_state=RANDOM_SEED,
        stratify=y,
    )
    validation_fraction_of_train_val = validation_size / (1 - test_size)
    x_train, x_val, y_train, y_val = train_test_split(
        x_train_val,
        y_train_val,
        test_size=validation_fraction_of_train_val,
        random_state=RANDOM_SEED,
        stratify=y_train_val,
    )

    pipeline = build_pipeline(x_train, y_train)
    pipeline.fit(x_train, y_train)

    validation_probabilities = pipeline.predict_proba(x_val)[:, 1]
    test_probabilities = pipeline.predict_proba(x_test)[:, 1]

    default_metrics = evaluate_predictions(y_test, test_probabilities, threshold=0.50)
    f2_threshold = choose_f2_threshold(y_val, validation_probabilities)
    f2_metrics = evaluate_predictions(
        y_test, test_probabilities, threshold=f2_threshold["threshold"]
    )

    roc_auc = roc_auc_score(y_test, test_probabilities)
    pr_auc = average_precision_score(y_test, test_probabilities)
    default_predictions = (test_probabilities >= 0.50).astype(int)

    metrics: dict[str, object] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_type": "XGBClassifier",
        "random_seed": RANDOM_SEED,
        "training_data_path": repo_display_path(training_data_path),
        "model_output_path": repo_display_path(model_output_path),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "row_counts": {
            "total": int(len(y)),
            "train": int(len(y_train)),
            "validation": int(len(y_val)),
            "test": int(len(y_test)),
            "delayed_total": int(y.sum()),
            "delayed_train": int(y_train.sum()),
            "delayed_validation": int(y_val.sum()),
            "delayed_test": int(y_test.sum()),
        },
        "default_threshold_metrics": default_metrics,
        "validation_selected_f2_threshold": f2_threshold,
        "test_metrics_at_validation_threshold": f2_metrics,
        "roc_auc": round(float(roc_auc), 4),
        "pr_auc": round(float(pr_auc), 4),
        "classification_report_default_threshold": classification_report(
            y_test,
            default_predictions,
            target_names=["not_delayed", "delayed"],
            zero_division=0,
            output_dict=True,
        ),
        "versions": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "sklearn": sklearn.__version__,
            "xgboost": xgboost.__version__,
        },
    }

    model_output_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_output_path)
    metrics_output_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return metrics


def print_metrics(metrics: dict[str, object]) -> None:
    default_metrics = metrics["default_threshold_metrics"]
    threshold_metrics = metrics["test_metrics_at_validation_threshold"]
    recommended = metrics["validation_selected_f2_threshold"]

    print("Phase 10 training complete")
    print(f"Model saved to: {metrics['model_output_path']}")
    print(f"Rows: {metrics['row_counts']}")
    print()
    print("Default threshold metrics (0.50):")
    print(f"  Accuracy:  {default_metrics['accuracy']}")
    print(f"  Precision: {default_metrics['precision_delayed']}")
    print(f"  Recall:    {default_metrics['recall_delayed']}")
    print(f"  F1:        {default_metrics['f1_delayed']}")
    print(f"  Confusion: {default_metrics['confusion_matrix']}")
    print()
    print(f"ROC-AUC: {metrics['roc_auc']}")
    print(f"PR-AUC:  {metrics['pr_auc']}")
    print()
    print("Validation-selected recall-oriented threshold:")
    print(f"  Threshold: {recommended['threshold']}")
    print("Untouched test metrics at that threshold:")
    print(f"  Precision: {threshold_metrics['precision_delayed']}")
    print(f"  Recall:    {threshold_metrics['recall_delayed']}")
    print(f"  F1:        {threshold_metrics['f1_delayed']}")


def main() -> None:
    args = parse_args()
    metrics = train_model(
        training_data_path=Path(args.training_data),
        model_output_path=Path(args.model_output),
        metrics_output_path=Path(args.metrics_output),
        test_size=args.test_size,
        validation_size=args.validation_size,
    )
    print_metrics(metrics)


if __name__ == "__main__":
    main()
