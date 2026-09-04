"""
src/llm/router.py
LLMRouter: tries providers in order, validates JSON, falls back to deterministic.

Fallback chain (configurable via .env):
  LLM_PRIMARY_PROVIDER=gemini
  LLM_FALLBACK_PROVIDERS=groq

Pipeline:
  1. Try primary provider
  2. If it fails, try each fallback in order
  3. Validate JSON response against LLMResponse schema
  4. If JSON is malformed, try to repair once, then move to next provider
  5. If all providers fail, use deterministic generator
  6. Never crash. Never expose API keys in logs.
"""
from __future__ import annotations
import os
import json
import logging
from dotenv import load_dotenv
from .base import LLMProvider
from .schema import LLMResponse
from .deterministic import generate_deterministic

load_dotenv()

logger = logging.getLogger("settle.llm")
logging.basicConfig(level=logging.INFO, format="[LLM] %(message)s")

_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))

# Prompt templates
_SYSTEM_PROMPT = """You are an expert settlement support AI for SettleAI.
You explain payment settlement statuses to support agents.
You MUST base your explanation STRICTLY on the evidence provided.
DO NOT invent facts, ETAs, amounts, or root causes not present in the evidence.
You MUST return valid JSON matching the schema exactly. No markdown, no code fences."""

_USER_PROMPT_TEMPLATE = """Analyse the following transaction evidence and return a JSON object.

EVIDENCE:
- Transaction ID: {transaction_id}
- Status: {status}
- Root Cause: {root_cause}
- Elapsed Time: {elapsed_minutes} minutes
- Confidence: {confidence}
- Exceptions: {exceptions}
- Recommended Action: {recommended_action}

REQUIRED JSON SCHEMA (return ONLY this JSON, no other text):
{{
  "status": "<SETTLED|DELAYED|FAILED|PENDING|UNKNOWN|AT_RISK|PROCESSING|UNRESOLVED>",
  "root_cause": "<root cause string>",
  "confidence": "<HIGH|MEDIUM|LOW>",
  "elapsed_minutes": <number>,
  "explanation": "<2-3 sentence plain English explanation grounded only in the evidence>",
  "recommended_action": "<action for support agent>",
  "exception_list": ["<exception1>", "<exception2>"]
}}"""


def _build_prompt(evidence_packet: dict) -> str:
    return _USER_PROMPT_TEMPLATE.format(
        transaction_id=evidence_packet.get("transaction_id", "N/A"),
        status=evidence_packet.get("status", "UNKNOWN"),
        root_cause=evidence_packet.get("root_cause", "N/A"),
        elapsed_minutes=evidence_packet.get("elapsed_minutes", 0),
        confidence=evidence_packet.get("confidence", "LOW"),
        exceptions=", ".join(evidence_packet.get("exceptions", [])) or "None",
        recommended_action=evidence_packet.get("recommended_action", "Manual review required."),
    )


def _try_parse_json(raw: str) -> dict | None:
    """Parse raw LLM output to JSON. Attempt one repair if needed."""
    raw = raw.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # One repair attempt: find first { and last }
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


def _validate_response(data: dict, provider_name: str) -> LLMResponse:
    """Build and validate an LLMResponse from parsed dict."""
    data["provider_used"] = provider_name
    data["is_fallback"]   = False
    data["fallback_reason"] = ""
    return LLMResponse(**data)


def _try_provider(
    provider: LLMProvider,
    prompt: str,
    evidence_packet: dict,
) -> LLMResponse | None:
    """
    Attempt generation from a single provider.
    Returns LLMResponse on success, None on any failure.
    """
    name = provider.get_provider_name()

    if not provider.is_available():
        logger.info(f"{name} skipped: API key not configured")
        return None

    for attempt in range(1, _MAX_RETRIES + 2):  # 1 + 1 retry
        try:
            raw = provider.generate(prompt, _SYSTEM_PROMPT)
            parsed = _try_parse_json(raw)

            if parsed is None:
                logger.warning(f"{name} returned malformed JSON (attempt {attempt})")
                if attempt <= _MAX_RETRIES:
                    continue  # one retry
                return None

            response = _validate_response(parsed, name)
            logger.info(f"{name} succeeded")
            return response

        except TimeoutError:
            logger.warning(f"{name} timed out (attempt {attempt})")
            return None  # no retry on timeout

        except Exception as exc:
            # Sanitise: never log API keys or full stack
            safe_msg = str(exc)[:120]
            logger.warning(f"{name} failed: {safe_msg} (attempt {attempt})")
            if attempt <= _MAX_RETRIES:
                continue
            return None

    return None


def _build_provider_chain() -> list[LLMProvider]:
    """
    Build provider list from env config.
    Primary first, then fallbacks in order.
    """
    from .providers.gemini import GeminiProvider
    from .providers.groq   import GroqProvider

    registry: dict[str, type[LLMProvider]] = {
        "gemini": GeminiProvider,
        "groq":   GroqProvider,
    }

    primary_name   = os.getenv("LLM_PRIMARY_PROVIDER", "gemini").strip().lower()
    fallback_names = [
        n.strip().lower()
        for n in os.getenv("LLM_FALLBACK_PROVIDERS", "groq").split(",")
        if n.strip()
    ]

    chain: list[LLMProvider] = []
    for name in [primary_name] + fallback_names:
        cls = registry.get(name)
        if cls:
            chain.append(cls())
        else:
            logger.warning(f"Unknown provider '{name}' in config — skipping")

    return chain


class LLMRouter:
    """
    Orchestrates the LLM fallback chain.
    Usage:
        router = LLMRouter()
        response = router.generate(evidence_packet)
    """

    def __init__(self) -> None:
        self._chain = _build_provider_chain()

    def generate(self, evidence_packet: dict) -> LLMResponse:
        """
        Try providers in order. Return deterministic fallback if all fail.
        Never raises. Always returns a valid LLMResponse.
        """
        prompt = _build_prompt(evidence_packet)

        for provider in self._chain:
            name = provider.get_provider_name()
            result = _try_provider(provider, prompt, evidence_packet)
            if result is not None:
                return result
            logger.info(f"Falling back from {name}")

        # All providers exhausted — deterministic fallback
        logger.warning("All providers failed — using deterministic fallback")
        return generate_deterministic(evidence_packet)
