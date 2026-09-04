# ML Engineer Task List

As the Machine Learning Engineer, your job is to build the predictive layer of the Settlement Intelligence Agent in parallel with the backend team. 

Since the `data/` folder now contains `gateway.csv`, `bank.csv`, `ledger.csv`, and `merged_history.csv` (which means **Phase 3 is complete**), you are completely unblocked to start working!

Here is your exact step-by-step checklist based on the `BUILD_PLAN.md`.

## Phase 9: Build the Training Table
* **File to create**: `scripts/build_training_data.py`
* **Objective**: Transform the raw CSVs into a structured dataset for XGBoost.
* **Tasks**:
  - [ ] Load the raw CSVs using Pandas.
  - [ ] **Define the Target**: Create a binary `is_delayed` column (`1` if `final_settlement_time > SLA`, else `0`).
  - [ ] **Enforce the Checkpoint**: Filter the data to represent exactly what is known at **10 minutes post-gateway**. 
  - [ ] **Prevent Target Leakage**: Ensure features like `final_ledger_timestamp` or `total_delay` are dropped from the training features.
  - [ ] **Prevent Contamination**: Remove any rows where `transaction_id` starts with `TXN_DEMO_` (so the model doesn't memorize the demo).
  - [ ] Save the output to `data/ml_training_ready.csv`.

## Phase 10: Train the XGBoost Model
* **File to create**: `scripts/train_model.py`
* **Objective**: Train a classification model to predict SLA breaches.
* **Tasks**:
  - [ ] Load `data/ml_training_ready.csv`.
  - [ ] Split the data into 80% train / 20% test (ensure you set `random_state=42` and `stratify=y` for reproducibility).
  - [ ] Build a Scikit-Learn `Pipeline` with a `OneHotEncoder` for categorical columns (e.g., `payment_method`, `bank_name`).
  - [ ] Train an `XGBClassifier`.
  - [ ] Evaluate the model on the test set. **Print out the Accuracy, Precision, Recall, and F1 Score.** Pay special attention to Recall for the delayed class!
  - [ ] Save the *entire* pipeline to `models/delay_model.joblib`.

## Phase 11: Build the Prediction Service
* **File to create**: `src/predictor.py`
* **Objective**: Create the inference wrapper that the backend team will call in production.
* **Tasks**:
  - [ ] Write a function `predict_delay_risk(feature_dict: dict) -> dict`.
  - [ ] Load `models/delay_model.joblib` inside (or at the top of) the module.
  - [ ] Map the incoming dictionary to a Pandas DataFrame of length 1.
  - [ ] Return a dictionary matching the agreed contract:
    ```python
    {
        "applicable": True,
        "risk_score": 0.84,
        "risk_level": "HIGH"  # E.g., HIGH if > 0.70
    }
    ```

## Phase 12: Build the ETA Estimator (Bonus / Parallel Task)
* **File to create**: `src/estimator.py`
* **Objective**: Estimate remaining time based on history (No ML needed).
* **Tasks**:
  - [ ] Write a function `estimate_additional_delay(bank_name, payment_method) -> dict`.
  - [ ] Load historical delayed transactions and calculate the median remaining delay for that specific bank and payment method.

---

> **Integration Point**: Once you finish `src/predictor.py` and `src/estimator.py`, tell the backend engineer! They will plug your functions directly into `src/service.py` at Hour 8.
