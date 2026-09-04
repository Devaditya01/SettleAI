"""Schema-validated evidence boundary for the explanation model.

The explanation model is deliberately downstream of the deterministic rules.
Only normalized, code-owned facts in :class:`EvidencePacket` may cross this
boundary. Raw gateway, bank, ledger, CSV, webhook, or log content is excluded.
"""

from __future__ import annotations

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.exceptions import VALID_CONFIDENCE_LEVELS, VALID_EXCEPTION_FLAGS
from src.recommendations import get_recommendation
from src.rules import VALID_ROOT_CAUSES, VALID_STATUSES


EVIDENCE_SCHEMA_VERSION = "1.0"
VALID_RISK_LEVELS = {"LOW", "MEDIUM", "HIGH"}


class EvidencePacket(BaseModel):
    """The complete and exclusive contract accepted by the LLM layer."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )

    schema_version: str = Field(default=EVIDENCE_SCHEMA_VERSION, pattern=r"^1\.0$")
    transaction_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    )
    status: str
    root_cause: str
    evidence_confidence: str
    elapsed_minutes: float | None = Field(default=None, ge=0, le=525_600)
    exception_codes: list[str] = Field(default_factory=list, max_length=16)
    recommended_action_code: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Z0-9_]+$",
    )
    support_action: str = Field(min_length=1, max_length=600)
    customer_safe_message: str = Field(min_length=1, max_length=500)
    ml_risk_level: str | None = None
    estimated_delay_minutes: float | None = Field(default=None, ge=0, le=525_600)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in VALID_STATUSES:
            raise ValueError("status is outside the deterministic vocabulary")
        return value

    @field_validator("root_cause")
    @classmethod
    def validate_root_cause(cls, value: str) -> str:
        if value not in VALID_ROOT_CAUSES:
            raise ValueError("root_cause is outside the deterministic vocabulary")
        return value

    @field_validator("evidence_confidence")
    @classmethod
    def validate_confidence(cls, value: str) -> str:
        if value not in VALID_CONFIDENCE_LEVELS:
            raise ValueError("evidence_confidence is outside the allowed vocabulary")
        return value

    @field_validator("exception_codes")
    @classmethod
    def validate_exception_codes(cls, values: list[str]) -> list[str]:
        invalid = sorted(set(values) - VALID_EXCEPTION_FLAGS)
        if invalid:
            raise ValueError("exception_codes contains unsupported values")
        if len(values) != len(set(values)):
            raise ValueError("exception_codes must not contain duplicates")
        return sorted(values)

    @field_validator("ml_risk_level")
    @classmethod
    def validate_risk_level(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_RISK_LEVELS:
            raise ValueError("ml_risk_level is outside the allowed vocabulary")
        return value

    @model_validator(mode="after")
    def validate_code_owned_recommendation(self) -> Self:
        """Reject recommendation text that did not come from the code-owned map."""
        expected = get_recommendation(self.root_cause)
        if self.recommended_action_code != expected["action"]:
            raise ValueError("recommended_action_code does not match root_cause")
        if self.support_action != expected["description"]:
            raise ValueError("support_action is not the approved deterministic text")
        if self.customer_safe_message != expected["customer_message"]:
            raise ValueError("customer_safe_message is not approved deterministic text")
        return self


def build_llm_evidence_packet(analysis: dict[str, Any]) -> EvidencePacket:
    """Select and validate the only facts that may be sent to the LLM.

    Unknown keys on ``analysis`` are intentionally ignored. In particular,
    ``trace``, raw source rows, and gateway summaries never enter the packet.
    """
    if not isinstance(analysis, dict):
        raise TypeError("analysis must be a dictionary")

    journey = analysis.get("journey") or {}
    recommendation = analysis.get("recommendation") or {}
    ml_prediction = analysis.get("ml_prediction") or {}
    eta_estimation = analysis.get("eta_estimation") or {}

    ml_risk_level = None
    if ml_prediction.get("applicable") is True:
        ml_risk_level = ml_prediction.get("risk_level")

    estimated_delay = None
    if eta_estimation.get("applicable") is True:
        estimated_delay = eta_estimation.get("estimated_additional_delay_minutes")

    return EvidencePacket(
        transaction_id=analysis.get("transaction_id"),
        status=analysis.get("status"),
        root_cause=analysis.get("root_cause"),
        evidence_confidence=analysis.get("evidence_confidence"),
        elapsed_minutes=journey.get("total_elapsed_minutes"),
        exception_codes=analysis.get("exceptions") or [],
        recommended_action_code=recommendation.get("action"),
        support_action=recommendation.get("description"),
        customer_safe_message=recommendation.get("customer_message"),
        ml_risk_level=ml_risk_level,
        estimated_delay_minutes=estimated_delay,
    )
