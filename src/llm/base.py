"""
src/llm/base.py
Abstract base class for all LLM providers.
"""
from __future__ import annotations
from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Interface every provider must implement."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> str:
        """
        Call the LLM and return raw text.
        Raise an exception on any failure so the router can catch it.
        """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Human-readable provider identifier, e.g. 'gemini'."""

    def is_available(self) -> bool:
        """
        Lightweight availability check.
        Default: True — real check is deferred to generate().
        Providers may override this if they have a cheap health check.
        Never makes an extra API request just to test availability.
        """
        return True
