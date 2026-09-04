# Predictive Settlement Intelligence Agent
## 12-Hour Sprint Build Plan & Roadmap

This document serves as the master guide for building the Predictive Settlement Intelligence Agent during our 12-hour sprint. It removes ambiguity, defines strict interfaces, and outlines exactly what we are building, phase by phase.

---

## 1. Product Overview & Goal
The product is an **evidence-grounded settlement support agent**. 
When a support agent enters a **Transaction ID or Date**, the system:
1. **Traces** the transaction across Gateway → Bank → Ledger data.
2. **Diagnoses** the current settlement state and identifies a likely root cause using deterministic rules.
3. **Predicts** the delay risk using an XGBoost ML model (only if the transaction is still in progress).
4. **Estimates** the likely remaining delay based on historical medians.
5. **Recommends** the next safest support action.
6. **Explains** the findings via an LLM, strictly grounded in the verified structured evidence.

**Core Workflow**: `Trace → Diagnose → Predict → Recommend → Explain`

> **Note**: We build the deterministic core first. We do not touch ML or LLMs until the foundation is proven. Never let two consecutive phases pass without a smoke test of the previous phase's output.

---

## 2. Phase-by-Phase Roadmap

### Phase 0: Freeze the Contract (0:00 - 0:20)
Before any code is written, the team must agree on the final backend contract. 
- Define a strict `TypedDict` or `Pydantic` schema for the `analyze_transaction(transaction_id: str)` response. 
- Validate outputs against this schema continuously to prevent silent integration failures later.

### Phase 1 & 2: Project Structure, Security & Configuration (0:20 - 0:45)
- Establish standard Python structure (`src/`, `data/`, `scripts/`, `models/`, `tests/`).
- **Security First**: Establish `.env` and `.gitignore` immediately. No API keys in source control from hour zero.
- **Reproducibility**: Set explicit `RANDOM_SEED` in `config.py` for data generation and ML splits.
- **Dependencies**: Create a `requirements.txt` with strictly pinned versions (e.g., `xgboost==2.0.3`) to prevent demo-day deployment surprises.
- Create `config.py` holding demo assumptions (e.g., `SETTLEMENT_SLA_MINUTES = 30`).

### Phase 3: Synthetic Data Generation (0:45 - 1:45)
- Generate 3,000–5,000 rows for `gateway.csv`, `bank.csv`, and `ledger.csv`.
- Create realistic, overlapping latency distributions (e.g., normal latency 2-15m, delayed 8-45m).
- Seed specific deterministic demo transactions (e.g., `TXN_DEMO_NORMAL`, `TXN_DEMO_AT_RISK`).

### Phase 4: Data Loader & Validation (1:45 - 2:25)
- Build `src/loader.py` and `src/validator.py` to parse timestamps, normalize statuses, and check for missing columns, duplicate records, and invalid IDs.

### Phase 5: Transaction Tracer & Journey (2:25 - 3:05)
- Build `src/tracer.py` to locate a transaction across all three CSVs.
- Build `src/journey.py` to calculate elapsed processing times between gateway, bank, and ledger, strictly avoiding the replacement of missing timestamps with `0`.

### Phase 6: Deterministic Settlement Status (3:05 - 3:35)
- Map the journey to clear product statuses: `SETTLED`, `FAILED`, `PROCESSING`, `AT_RISK`, `DELAYED`, and `UNRESOLVED`.
- *Crucial Rule*: If a transaction has crossed the SLA, it is `DELAYED`, not "84% chance of delay".

### Phase 7: Root-Cause Rule Engine (3:35 - 4:20)
- Build `src/rules.py` containing deterministic priority rules (e.g., definitive failures > amount mismatches > bank processing delays > ledger posting delays).
- The LLM does *not* decide the root cause.

### Phase 8: Exception Handling & State Transitions (4:20 - 4:50)
- Build `src/exceptions.py` to calculate Evidence Confidence (`HIGH`, `MEDIUM`, `LOW`) based on missing fields, and log exceptions.
- Explicitly map overlaps: e.g., A transaction with missing ledger data gets `UNRESOLVED` status and `LOW` confidence. 

**[HOUR 4.5 CHECKPOINT]**: The mandatory PS-8 core trace and diagnostic engine must work end-to-end here without ML. Execute smoke tests on all logic.

---

### Phase 9: ML Training Table (4:50 - 5:35)
- Build `scripts/build_training_data.py`.
- **Target**: `is_delayed = 1 if final_settlement_time > SLA else 0`.
- **Leakage Prevention**: Enforce a strict feature checkpoint (e.g., 10 mins post-gateway). Check for both *target leakage* and *feature leakage* (no future timestamps allowed as features).
- **Contamination Prevention**: Explicitly exclude all `TXN_DEMO_*` records from the training set so the model doesn't memorize demo cases.

### Phase 10: Train XGBoost Model (5:35 - 6:35)
- Build `scripts/train_model.py`.
- Train an XGBoost Classifier via a pipeline that includes categorical OneHotEncoding.
- Save the entire pipeline to `models/delay_model.joblib`. Ensure high recall for delayed transactions.

**[HOUR 6.5 CHECKPOINT]**: Smoke test the ML model inference with dummy data to ensure it returns predictions correctly.

### Phase 11: Prediction Service (6:35 - 6:55)
- Build `src/predictor.py`.
- Apply ML predictions *only* when the transaction is still processing and hasn't exceeded the SLA.

### Phase 12: ETA Estimator (6:55 - 7:25)
- Build `src/estimator.py`.
- Instead of complex ML, use historical similarity matching to calculate the median remaining delay.

### Phase 13: Recommendation Engine (7:25 - 7:45)
- Build `src/recommendations.py` to map deterministic causes to fixed operational actions.

### Phase 14: Service Orchestration (7:45 - 8:15)
- Build `src/service.py`. This integrates trace, rules, ML, ETA, and recommendations into the single `analyze_transaction()` contract agreed upon in Phase 0.
- **Failure Isolation**: If ML prediction or ETA estimators crash mid-request, catch the exception gracefully and return a `prediction unavailable / LOW confidence` state instead of breaking the entire orchestration flow.

**[HOUR 8.5 CHECKPOINT]**: The backend service `analyze_transaction()` must successfully return the defined Pydantic/TypedDict contract. Smoke test the orchestration.

### Phase 15: LLM Explanation (8:15 - 9:00)
- Build `src/llm.py` to convert the structured evidence packet into a plain-English explanation.
- Must include a deterministic fallback if the API fails, ensuring the demo is safe.

### Phase 16 & 17: Streamlit UI & Date Search (9:00 - 10:15)
- Build `app.py`. One clean screen displaying the sequence of evidence without over-complicating the frontend. 
- Implement a simple Date-to-Transaction-ID search list.

### Phase 18 & 19: Security & Responsible AI Wrap-Up (10:15 - 10:50)
- Confirm the LLM acts only on structured evidence (not raw CSVs) to prevent prompt injections.
- Finalize the `MODEL_CARD.md`.

### Phase 20 & 21: Testing & Demo Prep (10:50 - 12:00)
- Ensure the 10 core test edge cases (malicious input, missing banks, delays) pass.
- Rehearse the 3 core demo cases: Normal, At-Risk (showing ML innovation), and Missing Bank (showing Responsible AI exception handling).

---

## 3. Guiding Architectural Principle

The system must flow sequentially:
`Data → Truth → Rules → Prediction → Recommendation → Explanation`

If we fall behind schedule, we cut UI polish, charts, and LLM styling. We **never** cut the Tracer, Deterministic Status, or Exceptions.
