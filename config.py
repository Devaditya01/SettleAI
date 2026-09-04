"""Configuration settings for the Settlement Intelligence Agent."""

# Settlement SLAs and warning thresholds (in minutes)
SETTLEMENT_SLA_MINUTES = 30
PREDICTION_CHECKPOINT_MINUTES = 10
BANK_WARNING_MINUTES = 15
LEDGER_WARNING_MINUTES = 10
AT_RISK_THRESHOLD_MINUTES = 15

# ML risk thresholds
HIGH_RISK_THRESHOLD = 0.70
MEDIUM_RISK_THRESHOLD = 0.40

# Random seed for reproducibility
RANDOM_SEED = 42

# Defaults and paths
DEFAULT_CURRENCY = "INR"
DATA_DIR = "data"
MODEL_PATH = "models/delay_model.joblib"

# Valid status vocabularies
VALID_GATEWAY_STATUSES = {"SUCCESS", "FAILED", "PENDING"}
VALID_BANK_STATUSES = {"SETTLED", "PROCESSING", "FAILED", "NOT_FOUND"}
VALID_LEDGER_STATUSES = {"POSTED", "PENDING", "FAILED", "NOT_FOUND"}

# CSV column contracts
GATEWAY_REQUIRED_COLUMNS = [
    "transaction_id", "gateway_timestamp", "gateway_status",
    "gateway_response_code", "amount", "payment_method", "retry_count"
]
BANK_REQUIRED_COLUMNS = [
    "transaction_id", "bank_received_at", "bank_updated_at",
    "bank_status", "bank_response_code", "settlement_amount", "bank_name"
]
LEDGER_REQUIRED_COLUMNS = [
    "transaction_id", "ledger_timestamp", "ledger_status", "ledger_amount"
]
