"""
src/llm/providers/gemini.py
Gemini provider using the google-genai SDK.
Handles: rate limits, quota, model-not-found, timeout, network errors.
"""
from __future__ import annotations
import os
import json
import signal
from ..base import LLMProvider

_TIMEOUT = int(os.getenv("LLM_TIMEOUT_SECONDS", "15"))
_MODEL   = "gemini-flash-latest"

# Error substrings that indicate provider-level failures (safe to fallback)
_PROVIDER_ERRORS = (
    "429", "quota", "rate", "503", "502", "500",
    "unavailable", "not found", "timeout", "deadline",
    "resource_exhausted", "model",
)


def _is_provider_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in _PROVIDER_ERRORS)


class GeminiProvider(LLMProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("GEMINI_API_KEY", "")

    def get_provider_name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, prompt: str, system_prompt: str) -> str:
        if not self._api_key:
            raise RuntimeError("GEMINI_API_KEY not configured")

        from google import genai

        client = genai.Client(api_key=self._api_key)

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

        # Use a simple timeout via threading
        import threading
        result: dict = {"text": None, "error": None}

        def _call():
            try:
                response = client.models.generate_content(
                    model=_MODEL,
                    contents=full_prompt,
                    config={"temperature": 0.1, "max_output_tokens": 350},
                )
                result["text"] = getattr(response, "text", None) or ""
            except Exception as e:
                result["error"] = e

        thread = threading.Thread(target=_call, daemon=True)
        thread.start()
        thread.join(timeout=_TIMEOUT)

        if thread.is_alive():
            raise TimeoutError(f"Gemini timed out after {_TIMEOUT}s")

        if result["error"] is not None:
            raise result["error"]

        return result["text"] or ""
