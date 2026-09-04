# SettleAI Delay-Risk Model Card

## Model overview

SettleAI uses an `XGBClassifier` to estimate whether an in-progress, otherwise successful payment will miss the configured settlement service-level agreement (SLA). The model is advisory. Deterministic transaction tracing and rules remain the authoritative source for settlement status and root-cause diagnosis.

| Item | Value |
| --- | --- |
| Model artifact | `models/delay_model.joblib` |
| Model type | `XGBClassifier` |
| Model created | `2026-09-04T21:10:35.725784+00:00` |
| Prediction checkpoint | 10 minutes after gateway initiation |
| Settlement SLA | 30 minutes |
| Random seed | 42 |
| Decision threshold | 0.2393, selected on validation data using F2 |

## Intended use

The model supports payment-operations and customer-support staff by highlighting transactions that may need attention before they cross the SLA. The backend calls it only when a transaction is still `PROCESSING` or `AT_RISK`, has not already crossed the SLA, and deterministic rules have not produced a terminal or unresolved outcome.

The prediction should appear with deterministic evidence, model availability, model version, and any ETA basis. It is one input to human review.

## Out-of-scope use

The model must not:

- determine final settlement status or root cause;
- initiate or approve a refund, retry, payout, ledger change, or movement of funds;
- make credit, eligibility, fraud, compliance, or customer-access decisions;
- replace reconciliation with gateway, bank, and ledger evidence;
- be used for populations or payment systems without validation;
- present an ETA as a guarantee.

## Training data and target

The current dataset is synthetic and was built from internally consistent mock gateway, bank, and ledger records. It is useful for workflow testing and demonstration; it does not establish production performance.

| Population measure | Count |
| --- | ---: |
| Gateway rows read | 5,500 |
| Successful gateway rows | 5,174 |
| Rows with a final posted ledger entry | 3,996 |
| Rows settled by the 10-minute checkpoint and excluded | 2,025 |
| Rows without a usable training label | 1,178 |
| Final model population | 1,971 |
| Delayed rows | 354 (17.96%) |
| Not-delayed rows | 1,617 |
| Train / validation / test | 1,182 / 394 / 395 |

The target `is_delayed` is 1 when the final posted ledger timestamp is more than 30 minutes after gateway initiation. Rows already settled by the 10-minute prediction checkpoint are excluded. Final settlement information is used only to create the target.

## Features

The model uses the checkpoint-visible contract exported by `src.ml_features.FEATURE_COLUMNS`:

- `amount`
- `payment_method`
- `retry_count`
- `gateway_hour`
- `gateway_day_of_week`
- `gateway_is_weekend`
- `bank_observed_by_checkpoint`
- `bank_name_at_checkpoint`
- `bank_status_at_checkpoint`
- `bank_response_code_at_checkpoint`
- `bank_receive_lag_minutes`
- `bank_update_observed_by_checkpoint`
- `bank_age_minutes_at_checkpoint`
- `settlement_amount_at_checkpoint`
- `settlement_amount_delta_at_checkpoint`

Transaction IDs, final ledger timestamps, raw future timestamps, and post-hoc delay totals are excluded from model inputs.

## Evaluation

The threshold was selected on the validation split using F2, which weights recall more heavily than precision. The following figures are from the untouched 395-row test split.

| Metric | Test result at threshold 0.2393 |
| --- | ---: |
| Accuracy | 72.91% |
| Precision for delayed class | 38.61% |
| Recall for delayed class | 85.92% |
| F1 for delayed class | 53.28% |
| ROC AUC | 90.58% |
| PR AUC | 78.24% |
| True negatives / false positives | 227 / 97 |
| False negatives / true positives | 10 / 61 |

The selected operating point catches most delayed transactions but produces many false alerts. Support teams should treat a high-risk result as a prioritization signal, not proof of a delay. At the default 0.5 threshold, delayed precision was 56.04%, recall was 71.83%, and accuracy was 84.81%.

## Leakage controls

- Transaction ID is excluded from the default training output.
- Demo transaction IDs are excluded before feature construction.
- Final ledger timestamp is used only to label `is_delayed`.
- Rows settled by the prediction checkpoint are excluded from the model population.
- Raw future timestamps and post-hoc delay totals are excluded from features.
- Training and inference share the same `FEATURE_COLUMNS` definition.

## Responsible AI and human oversight

Deterministic rules decide `SETTLED`, `FAILED`, `PROCESSING`, `AT_RISK`, `DELAYED`, or `UNRESOLVED` and assign the root cause. The model is called only for eligible in-progress transactions. If model loading, feature extraction, or prediction fails, the service continues with deterministic evidence and marks the prediction unavailable.

Every financial action requires human review under the organisation's operational controls. Low-confidence or incomplete evidence must be shown as an exception, never filled with invented values. Operators should verify source records before refunds, retries, or escalation.

The explanation LLM is separated from the model and receives only a schema-validated, allowlisted evidence packet. It cannot access CSV files or change deterministic decisions. Provider failures, malformed output, unsupported numbers, or unsupported ETA claims trigger approved deterministic wording.

## Limitations

- All current data is synthetic; performance on real payment traffic is unknown.
- Synthetic class balance, bank behaviour, retry patterns, and latency distributions may differ materially from production.
- Holidays, outages, regional rails, processor changes, compliance holds, and new payment methods are not comprehensively represented.
- The model predicts SLA risk, not the causal reason for a delay.
- ROC AUC and PR AUC do not guarantee calibrated probabilities.
- No fairness claim can be made from the present dataset. Protected attributes are not model features, but proxy effects and different error rates across operational segments have not been assessed.
- Historical ETA estimates are segment medians and are not model guarantees.
- The recall-oriented threshold creates operational alert fatigue unless monitored.

## Security and privacy

The feature contract contains operational settlement fields and excludes customer names, card numbers, bank account numbers, authentication data, secrets, raw webhooks, free-form logs, and transaction IDs. Production data access must enforce merchant scope, least privilege, encryption in transit and at rest, retention limits, and auditable access.

The joblib artifact must be loaded only from a trusted deployment package. Joblib files can execute code during deserialization, so an artifact received from an untrusted source must never be loaded. Production releases should verify the artifact SHA-256 before loading.

## Monitoring and rollback

Monitor model-load failures, missing-feature rates, risk-score distribution, alert volume, prediction rate by bank and payment method, realized delay rate, precision, recall, false-negative rate, and feature drift. Review metrics after gateway or bank integration changes. Establish alert-volume limits and compare model alerts with deterministic outcomes.

If data validation fails, drift exceeds the approved limit, errors rise materially, or performance falls below the operational target, disable ML prediction and continue with deterministic tracing. Record the model version, threshold, evidence timestamp, and reason for every prediction.

## Reproducibility and provenance

The saved metrics record the following training environment:

| Dependency | Recorded version |
| --- | --- |
| Python | 3.14.5 |
| pandas | 3.0.5 |
| NumPy | 2.5.2 |
| scikit-learn | 1.9.0 |
| XGBoost | 3.4.1 |

The core model-library pins in `requirements.txt` match the versions recorded during training. A clean environment should still run the artifact and prediction tests before deployment because operating-system libraries and unrecorded transitive dependencies can differ. Byte-for-byte retraining is not claimed.

Verification commands:

```powershell
python scripts\build_training_data.py
python scripts\train_model.py
python tests\test_phase9.py
python tests\test_phase10.py
python tests\test_phase11.py
python tests\test_phase12.py
python -m pytest tests\test_phase18.py tests\test_phase19.py
```

Current artifact provenance:

| Artifact | SHA-256 |
| --- | --- |
| `models/delay_model.joblib` | `7752368423352C2F270248103EACF899B7E21797CD720CABF5157CA7C179393D` |
| `models/delay_model.metrics.json` | `C51325279B6D086C687EA726A3A4B8DCCFFE919EAA510B1760C7CDF29C337EE5` |
| `data/ml_training_ready.csv` | `D27D783F144274D1A8B0837891D2B261267B6A3907A838EC537680D86AAA2852` |
| `data/ml_training_ready.audit.json` | `51810F94ABDA7CB50ADF7DEABE042F4A7F5BCFF5812C1D62C355B51FD1299E90` |

## Ownership and review

- Status: Hackathon demonstration, not approved for production financial decisions.
- Review trigger: Any retraining, feature change, threshold change, new payment rail, new data source, or production-data introduction.
- Required reviewers for production: payments operations, model owner, security, privacy, and compliance.
