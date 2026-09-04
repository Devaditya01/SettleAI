"""
src/llm/schema.py
Pydantic schema for the validated LLM response.
Every code path — LLM or deterministic — must return this shape.
"""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, field_validator


VALID_STATUSES = {"SETTLED", "DELAYED", "FAILED", "PENDING", "UNKNOWN", "AT_RISK", "PROCESSING", "UNRESOLVED"}
VALID_CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}


class LLMResponse(BaseModel):
    status: str
    root_cause: str
    confidence: str
    elapsed_minutes: float
    explanation: str
    recommended_action: str
    exception_list: list[str] = []
    provider_used: str          # "gemini" | "groq" | "deterministic"
    is_fallback: bool = False
    fallback_reason: str = ""   # shown in UI if is_fallback=True

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in VALID_STATUSES:
            return "UNKNOWN"
        return upper

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: str) -> str:
        upper = v.upper().strip()
        if upper not in VALID_CONFIDENCE:
            return "LOW"
        return upper

    @field_validator("elapsed_minutes", mode="before")
    @classmethod
    def coerce_elapsed(cls, v) -> float:
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0
