"""Phase 9 runner: build the ML-ready training dataset.

The feature engineering lives in src/ml_features.py so Phase 10 training and
Phase 11 inference can share the same feature contract.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config import (  # noqa: E402
    DATA_DIR,
    PREDICTION_CHECKPOINT_MINUTES,
    SETTLEMENT_SLA_MINUTES,
)
from src.ml_features import (  # noqa: E402
    FEATURE_COLUMNS,
    TARGET_COLUMN,
    build_training_table,
)


DEFAULT_OUTPUT_PATH = ROOT_DIR / "data" / "ml_training_ready.csv"
DEFAULT_AUDIT_PATH = ROOT_DIR / "data" / "ml_training_ready.audit.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build data/ml_training_ready.csv for delay-risk modeling."
    )
    parser.add_argument("--data-dir", default=DATA_DIR)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT_PATH))
    parser.add_argument("--audit-output", default=str(DEFAULT_AUDIT_PATH))
    parser.add_argument(
        "--checkpoint-minutes",
        type=int,
        default=PREDICTION_CHECKPOINT_MINUTES,
        help="Prediction checkpoint after gateway capture.",
    )
    parser.add_argument(
        "--sla-minutes",
        type=int,
        default=SETTLEMENT_SLA_MINUTES,
        help="Settlement SLA used to create the binary target.",
    )
    parser.add_argument(
        "--include-ids",
        action="store_true",
        help="Include transaction_id for audit/debugging; off by default.",
    )
    return parser.parse_args()


def write_audit_file(path: Path, summary: dict[str, int | float]) -> None:
    audit = {
        "purpose": (
            "Predict whether an in-progress successful payment will miss the "
            "settlement SLA, using only checkpoint-visible evidence."
        ),
        "feature_columns": FEATURE_COLUMNS,
        "target_column": TARGET_COLUMN,
        "leakage_controls": [
            "transaction_id excluded from default training output",
            "demo transaction IDs excluded before feature building",
            "final ledger timestamp used only to label is_delayed",
            "rows already settled by checkpoint excluded from model population",
            "raw future timestamps and post-hoc delay totals excluded from features",
        ],
        "summary": summary,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(audit, indent=2), encoding="utf-8")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    args = parse_args()

    result = build_training_table(
        data_dir=args.data_dir,
        checkpoint_minutes=args.checkpoint_minutes,
        sla_minutes=args.sla_minutes,
        include_ids=args.include_ids,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.table.to_csv(output_path, index=False)

    audit_path = Path(args.audit_output)
    write_audit_file(audit_path, result.summary)

    print(f"Wrote {len(result.table)} rows to {output_path}")
    print(f"Wrote audit metadata to {audit_path}")
    print("Summary:")
    for key, value in result.summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
