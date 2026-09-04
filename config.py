"""
Configuration settings for the Settlement Intelligence Agent.
"""

# Settlement SLAs and warning thresholds (in minutes)
SETTLEMENT_SLA_MINUTES = 30
BANK_WARNING_MINUTES = 15
LEDGER_WARNING_MINUTES = 10
AT_RISK_THRESHOLD_MINUTES = 15

# Random seed for reproducibility
RANDOM_SEED = 42

# Default currency
DEFAULT_CURRENCY = "INR"
