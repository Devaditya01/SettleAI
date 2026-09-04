"""
Phase 15 — LLM Explanation Engine
===================================
Translates the structured evidence packet into a plain-English explanation.
Strictly acts only on the provided evidence to prevent hallucinations.
Includes a deterministic fallback in case the API fails.

Uses: google-genai SDK (new), gemini-2.5-flash model
"""

import os
from dotenv import load_dotenv

# Load GEMINI_API_KEY from .env
load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY")
_MODEL_NAME = "gemini-2.5-flash"

def fallback_explanation(evidence_packet: dict) -> str:
    """
    Returns a safe, hardcoded response if the LLM API fails or is unconfigured.
    Ensures the app never crashes during a demo.
    """
    status = evidence_packet.get("status", "UNKNOWN")
    action = evidence_packet.get("recommended_action", "Manual investigation required.")
    root_cause = evidence_packet.get("root_cause", "undetermined")
    return (
        f"Automated explanation is currently unavailable. "
        f"The transaction was diagnosed as {status} due to {root_cause}. "
        f"Recommended Action: {action}"
    )


def generate_explanation(evidence_packet: dict) -> str:
    """
    Generates a plain-English explanation of the settlement status
    based STRICTLY on the provided evidence packet.

    Args:
        evidence_packet (dict): Contains transaction_id, status, root_cause,
                                confidence, elapsed_minutes, exceptions, 
                                and recommended_action.

    Returns:
        str: LLM-generated explanation, or fallback string on failure.
    """
    # Guard: no API key → immediate fallback
    if not _api_key:
        return fallback_explanation(evidence_packet)

    try:
        from google import genai

        client = genai.Client(api_key=_api_key)

        prompt = f"""You are an expert settlement support AI for SettleAI.
Your job is to explain the transaction status to a support agent.
You MUST base your explanation STRICTLY on the evidence provided below.
DO NOT invent facts, ETAs, or root causes not listed in the evidence.
Keep it concise, professional, and actionable (2-3 sentences max).

EVIDENCE:
- Transaction ID: {evidence_packet.get("transaction_id", "N/A")}
- Current Status: {evidence_packet.get("status", "UNKNOWN")}
- Root Cause: {evidence_packet.get("root_cause", "N/A")}
- Time Elapsed: {evidence_packet.get("elapsed_minutes", "N/A")} minutes
- Confidence Level: {evidence_packet.get("confidence", "UNKNOWN")}
- Exceptions Found: {", ".join(evidence_packet.get("exceptions", [])) or "None"}
- Recommended Action: {evidence_packet.get("recommended_action", "N/A")}
"""

        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=prompt,
            config={"temperature": 0.1, "max_output_tokens": 150},
        )

        text = getattr(response, "text", None)
        if not text:
            return fallback_explanation(evidence_packet)

        return text.strip()

    except Exception as e:
        print(f"[LLM Warning] Generation failed: {e}")
        return fallback_explanation(evidence_packet)


# Manual test if run directly
if __name__ == "__main__":
    test_packet = {
        "transaction_id": "TXN_999",
        "status": "DELAYED",
        "root_cause": "BANK_PROCESSING_DELAY",
        "confidence": "HIGH",
        "elapsed_minutes": 42.5,
        "exceptions": ["SLA_BREACHED"],
        "recommended_action": "Contact bank ops team. Standard SLA is 30 mins."
    }
    print("=== Fallback Test ===")
    print(fallback_explanation(test_packet))
    print("\n=== Real LLM Test ===")
    print(generate_explanation(test_packet))
