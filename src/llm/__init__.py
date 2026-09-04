"""
src/llm/__init__.py
Public API for the LLM package.

Usage:
    from src.llm import generate_explanation, LLMResponse

The caller never needs to know which provider was used.
Check response.provider_used and response.is_fallback for UI display.
"""
from .router import LLMRouter
from .schema import LLMResponse
from .deterministic import generate_deterministic

# Module-level singleton — avoids rebuilding the chain on every call
_router: LLMRouter | None = None


def _get_router() -> LLMRouter:
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


def generate_explanation(evidence_packet: dict) -> LLMResponse:
    """
    Generate a validated settlement explanation.

    Tries configured LLM providers in order (primary → fallbacks),
    validates JSON response, and falls back to deterministic generation
    if all providers fail.

    Args:
        evidence_packet: Dict with keys:
            transaction_id, status, root_cause, confidence,
            elapsed_minutes, exceptions, recommended_action

    Returns:
        LLMResponse — always valid, never raises.
    """
    return _get_router().generate(evidence_packet)


__all__ = ["generate_explanation", "LLMResponse", "generate_deterministic"]
