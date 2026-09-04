"""
src/llm/providers/groq.py
Groq provider using the requests library (free-tier compatible).
Model: llama-3.1-8b-instant (fast, free on Groq).
Handles: rate limits, quota, timeout, network errors.
"""
from __future__ import annotations
import os
import json
import requests
from ..base import LLMProvider

_TIMEOUT = int(os.getenv("LLM_TIMEOUT_SECONDS", "15"))
_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_MODEL = "llama-3.1-8b-instant"


class GroqProvider(LLMProvider):
    def __init__(self) -> None:
        self._api_key = os.getenv("GROQ_API_KEY", "")

    def get_provider_name(self) -> str:
        return "groq"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, prompt: str, system_prompt: str) -> str:
        if not self._api_key:
            raise RuntimeError("GROQ_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": _MODEL,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 350,
        }

        try:
            resp = requests.post(
                _GROQ_URL,
                headers=headers,
                json=payload,
                timeout=_TIMEOUT,
            )
        except requests.Timeout:
            raise TimeoutError(f"Groq timed out after {_TIMEOUT}s")
        except requests.ConnectionError as e:
            raise RuntimeError(f"Groq network error: {e}")

        if resp.status_code == 429:
            raise RuntimeError("Groq: 429 rate limit")
        if resp.status_code >= 500:
            raise RuntimeError(f"Groq: server error {resp.status_code}")
        if resp.status_code != 200:
            raise RuntimeError(f"Groq: unexpected status {resp.status_code}")

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return content.strip()
