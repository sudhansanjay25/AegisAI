"""
LLM Judge — uses Groq to determine if LLM output contains vault data.
This module is scaffolded now and will be fully wired in at Hour 9–13.
"""

import json

from groq import AsyncGroq

from app.config import settings

JUDGE_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama-3.1-8b-instant"

JUDGE_SYSTEM_PROMPT = """You are a data-leak detection judge. You will be given:
1. OUTPUT — text produced by an LLM
2. VAULT_CHUNKS — sensitive document chunks from a secure vault

Your job: compare the OUTPUT against the provided VAULT_CHUNKS only.
Decide if the OUTPUT asserts facts only present in the VAULT_CHUNKS, even if reworded.

You must only return "leak" if you can quote or precisely paraphrase a SPECIFIC fact
(a name, number, date, or identifier) that appears in the VAULT_CHUNKS and also appears,
however reworded, in the OUTPUT. If you cannot point to a specific shared fact, return
"no_leak" — even if the topics feel related. Vague thematic similarity is NOT sufficient
grounds for a leak verdict. In "matched_facts", list the specific facts found in BOTH
the output and the vault chunk — if this list would be empty, the verdict must be "no_leak".

Respond with strict JSON in this exact format:
{
  "verdict": "leak" | "no_leak",
  "confidence": 0.0 to 1.0,
  "matched_facts": ["list of specific facts from OUTPUT that match VAULT_CHUNKS"],
  "reason": "brief explanation of your verdict"
}"""


def _get_client() -> AsyncGroq:
    """Create a Groq client (lazy, no persistent state needed)."""
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set — cannot run judge")
    return AsyncGroq(api_key=settings.GROQ_API_KEY)


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
    
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": f"OUTPUT:\n{output_text}\n\nVAULT_CHUNKS:\n{chunks_text}"},
    ]

    import groq
    import logging

    for model in (JUDGE_MODEL, FALLBACK_MODEL):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0,
            )
            result = json.loads(response.choices[0].message.content)
            result["judge_model_used"] = model
            return result
        except (groq.RateLimitError, groq.InternalServerError, groq.APIConnectionError) as e:
            logging.warning(f"[JUDGE FALLBACK] {model} failed, trying next tier: {e}")
            continue
        except Exception as e:
            # Non-rate-limit errors (e.g. prompt too long, bad JSON): don't blindly retry
            logging.error(f"[JUDGE ERROR] {model} failed with non-retryable error: {e}")
            raise
    
    # Both models exhausted (or single model exhausted if only one is configured)
    raise RuntimeError("Both primary and fallback models exhausted due to rate limits")
