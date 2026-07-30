"""
LLM Judge — uses Groq to determine if LLM output contains vault data.
This module is scaffolded now and will be fully wired in at Hour 9–13.
"""

import json

from groq import Groq

from app.config import settings

JUDGE_MODEL = "llama-3.3-70b-versatile"

JUDGE_SYSTEM_PROMPT = """You are a data-leak detection judge. You will be given:
1. OUTPUT — text produced by an LLM
2. VAULT_CHUNKS — sensitive document chunks from a secure vault

Your job: determine whether the OUTPUT contains factual information that could
only have come from the VAULT_CHUNKS (not general knowledge).

Respond with a JSON object:
{
  "judge_verdict": "leak" | "clean" | "uncertain",
  "confidence": 0.0 to 1.0,
  "matched_facts": ["list of specific facts from OUTPUT that match VAULT_CHUNKS"],
  "reasoning": "brief explanation of your verdict"
}

Be strict: paraphrased or restructured vault data still counts as a leak.
General knowledge that happens to overlap does NOT count."""


def _get_client() -> Groq:
    """Create a Groq client (lazy, no persistent state needed)."""
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set — cannot run judge")
    return Groq(api_key=settings.GROQ_API_KEY)


def judge_factual_overlap(output_text: str, matched_chunks: list[str]) -> dict:
    """Ask the LLM judge whether output_text leaks data from matched_chunks.

    Args:
        output_text: The LLM-generated text to evaluate.
        matched_chunks: Vault chunks that were similarity-matched to the output.

    Returns:
        Dict with judge_verdict, confidence, matched_facts, reasoning.
    """
    client = _get_client()
    chunks_text = "\n---\n".join(matched_chunks)

    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"OUTPUT:\n{output_text}\n\nVAULT_CHUNKS:\n{chunks_text}",
            },
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    return json.loads(response.choices[0].message.content)
