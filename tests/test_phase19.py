"""Phase 19 checks that model-card claims stay tied to saved artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_model_card_exists_and_covers_responsible_ai_requirements():
    card = (ROOT / "MODEL_CARD.md").read_text(encoding="utf-8")
    required_topics = [
        "Intended use",
        "Out-of-scope use",
        "Training data",
        "Evaluation",
        "Leakage controls",
        "Limitations",
        "Human oversight",
        "Security and privacy",
        "Monitoring",
        "Reproducibility",
    ]
    for topic in required_topics:
        assert topic.lower() in card.lower()


def test_model_card_metrics_match_saved_metrics():
    metrics = json.loads(
        (ROOT / "models" / "delay_model.metrics.json").read_text(encoding="utf-8")
    )
    card = (ROOT / "MODEL_CARD.md").read_text(encoding="utf-8")
    selected = metrics["test_metrics_at_validation_threshold"]

    expected_values = [
        metrics["model_type"],
        f"{metrics['row_counts']['total']:,}",
        f"{metrics['row_counts']['delayed_total']:,}",
        f"{selected['threshold']:.4f}",
        f"{selected['accuracy'] * 100:.2f}%",
        f"{selected['precision_delayed'] * 100:.2f}%",
        f"{selected['recall_delayed'] * 100:.2f}%",
        f"{selected['f1_delayed'] * 100:.2f}%",
        f"{metrics['roc_auc'] * 100:.2f}%",
        f"{metrics['pr_auc'] * 100:.2f}%",
    ]
    for value in expected_values:
        assert value in card

    for feature in metrics["feature_columns"]:
        assert f"`{feature}`" in card


def test_model_card_records_current_artifact_hash():
    artifact = ROOT / "models" / "delay_model.joblib"
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest().upper()
    card = (ROOT / "MODEL_CARD.md").read_text(encoding="utf-8")
    assert digest in card
