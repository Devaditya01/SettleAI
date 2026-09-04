"""
tests/test_llm_fallback.py
Tests for the LLM fallback system — scenarios A through G.
Run with: pytest tests/test_llm_fallback.py -v
"""
import json
import pytest
from unittest.mock import patch, MagicMock

# Ensure src is importable
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm import generate_explanation, LLMResponse
from src.llm.router import LLMRouter, _try_parse_json
from src.llm.deterministic import generate_deterministic
from src.llm.schema import LLMResponse as SchemaResponse


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

SAMPLE_EVIDENCE = {
    "transaction_id": "TXN_TEST_001",
    "status": "DELAYED",
    "root_cause": "BANK_PROCESSING_DELAY",
    "confidence": "HIGH",
    "elapsed_minutes": 45.2,
    "exceptions": ["SLA_BREACHED"],
    "recommended_action": "Contact bank ops team. Standard SLA is 30 mins.",
}

VALID_LLM_JSON = json.dumps({
    "status": "DELAYED",
    "root_cause": "BANK_PROCESSING_DELAY",
    "confidence": "HIGH",
    "elapsed_minutes": 45.2,
    "explanation": "Transaction TXN_TEST_001 is delayed due to bank processing.",
    "recommended_action": "Contact bank ops team.",
    "exception_list": ["SLA_BREACHED"],
})


# ---------------------------------------------------------------------------
# A. Gemini succeeds → Gemini response returned
# ---------------------------------------------------------------------------

def test_A_gemini_succeeds():
    """When Gemini returns valid JSON, it should be used as the response."""
    with patch("src.llm.providers.gemini.GeminiProvider.generate", return_value=VALID_LLM_JSON), \
         patch.dict(os.environ, {"GEMINI_API_KEY": "test-key", "LLM_PRIMARY_PROVIDER": "gemini"}):
        router = LLMRouter()
        result = router.generate(SAMPLE_EVIDENCE)

    assert isinstance(result, LLMResponse)
    assert result.provider_used == "gemini"
    assert result.is_fallback is False
    assert result.status == "DELAYED"


# ---------------------------------------------------------------------------
# B. Gemini returns 429 → fallback provider called
# ---------------------------------------------------------------------------

def test_B_gemini_429_falls_back_to_groq():
    """When Gemini raises a 429, Groq should be called next."""
    with patch("src.llm.providers.gemini.GeminiProvider.generate",
               side_effect=RuntimeError("429 rate limit exceeded")), \
         patch("src.llm.providers.groq.GroqProvider.generate", return_value=VALID_LLM_JSON), \
         patch.dict(os.environ, {
             "GEMINI_API_KEY": "test-key",
             "GROQ_API_KEY": "test-key",
             "LLM_PRIMARY_PROVIDER": "gemini",
             "LLM_FALLBACK_PROVIDERS": "groq",
         }):
        router = LLMRouter()
        result = router.generate(SAMPLE_EVIDENCE)

    assert result.provider_used == "groq"
    assert result.is_fallback is False


# ---------------------------------------------------------------------------
# C. Gemini times out → fallback called
# ---------------------------------------------------------------------------

def test_C_gemini_timeout_falls_back():
    """When Gemini times out, should fall back to Groq."""
    with patch("src.llm.providers.gemini.GeminiProvider.generate",
               side_effect=TimeoutError("Gemini timed out after 15s")), \
         patch("src.llm.providers.groq.GroqProvider.generate", return_value=VALID_LLM_JSON), \
         patch.dict(os.environ, {
             "GEMINI_API_KEY": "test-key",
             "GROQ_API_KEY": "test-key",
             "LLM_PRIMARY_PROVIDER": "gemini",
             "LLM_FALLBACK_PROVIDERS": "groq",
         }):
        router = LLMRouter()
        result = router.generate(SAMPLE_EVIDENCE)

    assert result.provider_used == "groq"


# ---------------------------------------------------------------------------
# D. Gemini returns malformed JSON → fallback called
# ---------------------------------------------------------------------------

def test_D_malformed_json_falls_back():
    """When Gemini returns text that cannot be repaired to valid JSON, fall back."""
    with patch("src.llm.providers.gemini.GeminiProvider.generate",
               return_value="Sorry I cannot do that right now. Please try again."), \
         patch("src.llm.providers.groq.GroqProvider.generate", return_value=VALID_LLM_JSON), \
         patch.dict(os.environ, {
             "GEMINI_API_KEY": "test-key",
             "GROQ_API_KEY": "test-key",
             "LLM_PRIMARY_PROVIDER": "gemini",
             "LLM_FALLBACK_PROVIDERS": "groq",
             "LLM_MAX_RETRIES": "1",
         }):
        router = LLMRouter()
        result = router.generate(SAMPLE_EVIDENCE)

    assert result.provider_used == "groq"


# ---------------------------------------------------------------------------
# E. Gemini + Groq both fail → deterministic fallback returned
# ---------------------------------------------------------------------------

def test_E_all_providers_fail_deterministic():
    """When all LLM providers fail, deterministic fallback must be returned."""
    with patch("src.llm.providers.gemini.GeminiProvider.generate",
               side_effect=RuntimeError("quota exceeded")), \
         patch("src.llm.providers.groq.GroqProvider.generate",
               side_effect=RuntimeError("503 service unavailable")), \
         patch.dict(os.environ, {
             "GEMINI_API_KEY": "test-key",
             "GROQ_API_KEY": "test-key",
             "LLM_PRIMARY_PROVIDER": "gemini",
             "LLM_FALLBACK_PROVIDERS": "groq",
         }):
        router = LLMRouter()
        result = router.generate(SAMPLE_EVIDENCE)

    assert result.provider_used == "deterministic"
    assert result.is_fallback is True
    assert result.status == "DELAYED"


# ---------------------------------------------------------------------------
# F. All providers unavailable (no API keys) → deterministic still works
# ---------------------------------------------------------------------------

def test_F_no_api_keys_deterministic():
    """With no API keys configured, deterministic fallback must still work."""
    with patch.dict(os.environ, {
        "GEMINI_API_KEY": "",
        "GROQ_API_KEY": "",
        "LLM_PRIMARY_PROVIDER": "gemini",
        "LLM_FALLBACK_PROVIDERS": "groq",
    }):
        router = LLMRouter()
        result = router.generate(SAMPLE_EVIDENCE)

    assert isinstance(result, LLMResponse)
    assert result.provider_used == "deterministic"
    assert len(result.explanation) > 10  # must have real content
    assert result.status != ""


# ---------------------------------------------------------------------------
# G. Valid successful response → schema validation passes
# ---------------------------------------------------------------------------

def test_G_schema_validation():
    """A valid LLM response must pass Pydantic schema validation."""
    data = json.loads(VALID_LLM_JSON)
    data["provider_used"] = "gemini"
    data["is_fallback"] = False
    data["fallback_reason"] = ""
    response = SchemaResponse(**data)

    assert response.status == "DELAYED"
    assert response.confidence == "HIGH"
    assert response.provider_used == "gemini"
    assert isinstance(response.exception_list, list)


# ---------------------------------------------------------------------------
# Bonus: JSON repair utility
# ---------------------------------------------------------------------------

def test_json_repair_with_markdown_fences():
    """JSON wrapped in markdown fences should be successfully parsed."""
    raw = "```json\n{\"status\": \"SETTLED\"}\n```"
    result = _try_parse_json(raw)
    assert result is not None
    assert result["status"] == "SETTLED"


def test_json_repair_with_surrounding_text():
    """JSON embedded in surrounding text should be extracted and parsed."""
    raw = 'Here is the result: {"status": "DELAYED", "root_cause": "BANK_PROCESSING_DELAY"}'
    result = _try_parse_json(raw)
    assert result is not None


def test_deterministic_never_crashes():
    """Deterministic fallback must work even with a completely empty evidence packet."""
    result = generate_deterministic({})
    assert isinstance(result, LLMResponse)
    assert result.provider_used == "deterministic"
    assert result.is_fallback is True
