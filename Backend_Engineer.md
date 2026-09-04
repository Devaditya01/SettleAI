# Backend Engineer Task List

As the Backend Engineer, your job is to build the **deterministic core** of the Settlement Intelligence Agent. Your work is the foundation of the entire system—if your trace and rules fail, the ML and LLM will fail. 

You must strictly follow the principle: `Data → Truth → Rules`.

Here is your exact step-by-step checklist based on the `BUILD_PLAN.md`.

## Phase 0, 1 & 2: Project Setup & Security
* **Objective**: Lock the contracts and secure the environment.
* **Tasks**:
  - [ ] Create the core folders: `src/`, `models/`, `tests/`.
  - [ ] Create `.env` and `.env.example` (add `GEMINI_API_KEY=` or `GROQ_API_KEY=`). **Ensure `.env` is in `.gitignore`**.
  - [ ] Create `requirements.txt` with pinned versions (e.g., `pandas`, `pydantic`, `google-generativeai`).
  - [ ] Create `config.py` holding `SETTLEMENT_SLA_MINUTES = 30` and `RANDOM_SEED = 42`.
  - [ ] **Freeze the Contract**: Define a `TypedDict` or `Pydantic` schema for what `analyze_transaction()` will eventually return.

## Phase 4: Data Loader & Validator
* **Files to create**: `src/loader.py`, `src/validator.py`
* **Objective**: Safely load the CSVs and validate the data.
* **Tasks**:
  - [ ] Load `gateway.csv`, `bank.csv`, and `ledger.csv` into memory.
  - [ ] Validate that the inputted `transaction_id` matches a safe regex (e.g., `^[A-Za-z0-9_-]{1,64}$`).
  - [ ] Ensure missing records are treated as `None` (do not fake data or replace missing timestamps with `0`).

## Phase 5: Transaction Tracer & Journey
* **Files to create**: `src/tracer.py`, `src/journey.py`
* **Objective**: Trace the payment across the 3 systems.
* **Tasks**:
  - [ ] Write `trace_transaction(tx_id)` to pull the matching row from Gateway, Bank, and Ledger.
  - [ ] Write logic to calculate the elapsed times (Gateway → Bank, Bank Processing, Bank → Ledger).

## Phase 6 & 7: Deterministic Rules Engine
* **File to create**: `src/rules.py`
* **Objective**: Diagnose the root cause and product status using hard if/else logic.
* **Tasks**:
  - [ ] Map the journey to a product status (`SETTLED`, `FAILED`, `PROCESSING`, `AT_RISK`, `DELAYED`, `UNRESOLVED`). *Remember: If total time > SLA, it is `DELAYED`.*
  - [ ] Implement priority-based root-cause rules:
    1. Invalid/inconsistent evidence
    2. Definitive failure
    3. Amount mismatch
    4. Missing evidence
    5. Successful settlement
    6. Bank delay
    7. Ledger delay
    8. Retry/duplicate
    9. Undetermined

## Phase 8: Exceptions & Confidence
* **File to create**: `src/exceptions.py`
* **Objective**: Handle missing evidence honestly.
* **Tasks**:
  - [ ] Calculate Evidence Confidence (`HIGH`, `MEDIUM`, `LOW`). If a core record (like bank) is missing, confidence is `LOW`.
  - [ ] Append exceptions (e.g., `BANK_RECORD_MISSING`) to an exceptions array.

> 🛑 **HOUR 4.5 CHECKPOINT**: Stop here! You must write a small script to test that `TXN_DEMO_NORMAL` and `TXN_DEMO_MISSING_BANK` pass cleanly through `loader -> tracer -> rules -> exceptions` without crashing.

---

## Phase 13 & 15: Recommendations & LLM
* **Files to create**: `src/recommendations.py`, `src/llm.py`
* **Objective**: Map causes to actions, and generate human-readable text.
* **Tasks**:
  - [ ] Create a fixed lookup dictionary mapping root causes (e.g., `BANK_PROCESSING_DELAY`) to deterministic action text.
  - [ ] Write `generate_explanation(evidence_packet)`. The LLM prompt MUST instruct the model to act only on the provided packet and never invent facts.
  - [ ] **CRITICAL**: Implement a `fallback_explanation()` that returns a hardcoded string if the LLM API fails.

## Phase 14: Service Orchestration
* **File to create**: `src/service.py`
* **Objective**: The master integration file.
* **Tasks**:
  - [ ] Write `analyze_transaction(tx_id)` which calls all the files above in sequence.
  - [ ] Call the ML Engineer's `predict_delay_risk` and `estimate_additional_delay` functions.
  - [ ] **Failure Isolation**: Wrap the ML and LLM calls in `try/except` blocks. If they fail, degrade the response gracefully instead of crashing the function.
  - [ ] Validate the final dictionary against the Pydantic schema from Phase 0 before returning it to the frontend.
