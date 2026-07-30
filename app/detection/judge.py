"""
LLM Judge — uses Groq to determine if LLM output contains vault data.
This module is scaffolded now and will be fully wired in at Hour 9–13.
"""

import json

from groq import AsyncGroq

from app.config import settings

JUDGE_MODEL = "llama-3.3-70b-versatile"

JUDGE_SYSTEM_PROMPT = """You are a data-leak detection judge. You will be given:
1. OUTPUT — text produced by an LLM
2. VAULT_CHUNKS — sensitive document chunks from a secure vault

Your job: compare the OUTPUT against the provided VAULT_CHUNKS only.
Decide if the OUTPUT asserts facts only present in the VAULT_CHUNKS, even if reworded.

Respond with strict JSON in this exact format:
{
  "verdict": "leak" | "no_leak",
  "confidence": 0.0 to 1.0,
  "matched_facts": ["list of specific facts from OUTPUT that match VAULT_CHUNKS"],
  "reason": "brief explanation of your verdict"
}

Be strict: paraphrased or restructured vault data still counts as a leak.
General knowledge that happens to overlap does NOT count."""


def _get_client() -> AsyncGroq:
    """Create a Groq client (lazy, no persistent state needed)."""
    return AsyncGroq(api_key="gsk_badkey12345")


async def judge_factual_overlap(output_text: str, matched_chunks: list[str]) -> dict:
    """Ask the LLM judge whether output_text leaks data from matched_chunks.

    Args:
        output_text: The LLM-generated text to evaluate.
        matched_chunks: Vault chunks that were similarity-matched to the output.

    Returns:
        Dict with verdict, confidence, matched_facts, reason.
    """
    client = _get_client()
    chunks_text = "\n---\n".join(matched_chunks)

    response = await client.chat.completions.create(
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
