"""
Input validation for the Settlement Intelligence Agent.

Every user-facing input passes through this module before
touching any business logic. This is the first line of defence
against injection, path traversal, and malformed requests.
"""

import re
from datetime import datetime


# Pre-compiled regex — compiled once at import time, not per call.
_TRANSACTION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

_DATE_FORMAT = "%Y-%m-%d"


def validate_transaction_id(transaction_id: str) -> str:
    """Sanitize and validate a transaction ID.

    Args:
        transaction_id: Raw user input.

    Returns:
        The cleaned transaction ID string.

    Raises:
        ValueError: If the input is empty, too long, or contains
                     characters outside [A-Za-z0-9_-].
    """
    if not isinstance(transaction_id, str):
        raise ValueError("Transaction ID must be a string.")

    cleaned = transaction_id.strip()

    if not cleaned:
        raise ValueError("Transaction ID cannot be empty.")

    if not _TRANSACTION_ID_PATTERN.match(cleaned):
        raise ValueError(
            f"Invalid transaction ID: '{cleaned}'. "
            "Only alphanumeric characters, hyphens, and underscores are allowed (max 64 chars)."
        )

    return cleaned


def validate_date_input(date_string: str) -> datetime:
    """Validate and parse a date string in YYYY-MM-DD format.

    Args:
        date_string: Raw user input.

    Returns:
        A datetime.date object.

    Raises:
        ValueError: If the string is not valid YYYY-MM-DD.
    """
    if not isinstance(date_string, str):
        raise ValueError("Date input must be a string.")

    cleaned = date_string.strip()

    if not cleaned:
        raise ValueError("Date input cannot be empty.")

    try:
        parsed = datetime.strptime(cleaned, _DATE_FORMAT)
    except ValueError:
        raise ValueError(
            f"Invalid date format: '{cleaned}'. Expected YYYY-MM-DD."
        )

    return parsed.date()
