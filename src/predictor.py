"""Delay-risk prediction service for Phase 11.

The backend should call predict_delay_risk only after deterministic rules have
confirmed that ML is applicable: the transaction is still processing and has
not already crossed the SLA.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from config import HIGH_RISK_THRESHOLD, MEDIUM_RISK_THRESHOLD, MODEL_PATH
from src.ml_features import FEATURE_COLUMNS


DEFAULT_CLASSIFICATION_THRESHOLD = 0.50
METRICS_PATH = Path(MODEL_PATH).with_name("delay_model.metrics.json")


def _unavailable_response(reason: str) -> dict[str, Any]:
    return {
        "applicable": False,
        "risk_score": None,
        "risk_level": "UNKNOWN",
        "predicted_delayed": None,
        "threshold_used": None,
        "model_version": None,
        "reason": reason,
    }


@lru_cache(maxsize=1)
def _load_model(model_path: str = MODEL_PATH):
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(f"Delay model artifact not found: {path}")
    return joblib.load(path)


@lru_cache(maxsize=1)
def _load_model_metadata(metrics_path: str = str(METRICS_PATH)) -> dict[str, Any]:
    path = Path(metrics_path)
    if not path.is_file():
        return {
            "threshold": DEFAULT_CLASSIFICATION_THRESHOLD,
            "model_version": None,
        }

    metrics = json.loads(path.read_text(encoding="utf-8"))
    threshold = (
        metrics.get("validation_selected_f2_threshold", {})
        .get("threshold", DEFAULT_CLASSIFICATION_THRESHOLD)
    )

    return {
        "threshold": float(threshold),
        "model_version": metrics.get("created_at_utc"),
    }


def _risk_level(risk_score: float) -> str:
    if risk_score >= HIGH_RISK_THRESHOLD:
        return "HIGH"
    if risk_score >= MEDIUM_RISK_THRESHOLD:
        return "MEDIUM"
    return "LOW"


def _feature_frame(feature_dict: dict[str, Any]) -> pd.DataFrame:
    if not isinstance(feature_dict, dict):
        raise ValueError("feature_dict must be a dictionary.")

    missing = [column for column in FEATURE_COLUMNS if column not in feature_dict]
    if missing:
        raise ValueError(f"Missing required model features: {missing}")

    row = {column: feature_dict[column] for column in FEATURE_COLUMNS}
    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


def predict_delay_risk(feature_dict: dict[str, Any]) -> dict[str, Any]:
    """Predict settlement delay risk for a single checkpoint feature row.

    Args:
        feature_dict: Dictionary containing exactly the Phase 9/10 feature
            contract. Extra keys are ignored; missing required keys raise a
            contract error.

    Returns:
        A backend-friendly prediction dictionary with probability, risk level,
        classification threshold, and applicability metadata.
    """
    try:
        features = _feature_frame(feature_dict)
    except ValueError as exc:
        raise ValueError(f"Invalid prediction input: {exc}") from exc

    try:
        model = _load_model()
        metadata = _load_model_metadata()
        risk_score = float(model.predict_proba(features)[0][1])
        threshold = float(metadata["threshold"])

        return {
            "applicable": True,
            "risk_score": round(risk_score, 4),
            "risk_level": _risk_level(risk_score),
            "predicted_delayed": bool(risk_score >= threshold),
            "threshold_used": threshold,
            "model_version": metadata["model_version"],
            "reason": None,
        }
    except Exception as exc:
        return _unavailable_response(f"Prediction unavailable: {exc}")
