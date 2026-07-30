"""
Scoring router — evaluates an LLM output against the vault.
"""

import asyncio
from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ingestion.embed import embed_batch
from app.detection.similarity import find_similar_chunks
from app.detection.judge import judge_factual_overlap
from app.models import ScoredOutput
from app.config import settings

router = APIRouter(tags=["scoring"])


class ScoreRequest(BaseModel):
    output_text: str
    agent_id: str | None = None
    session_id: str | None = None


@router.post("/v1/outputs/score")
async def score_output(payload: ScoreRequest, session: AsyncSession = Depends(get_session)):
    """Score an incoming LLM output against the vault using cosine similarity and LLM judge."""
    
    # 1. Embed the incoming output text
    [embedding] = embed_batch([payload.output_text])
    
    # 2. Find the closest matching chunks in the vault
    matches = await find_similar_chunks(session, embedding, top_k=5)

    # Use the highest similarity score (the first match) as the overall score
    top_similarity = matches[0].similarity if matches else 0.0
    matched_ids = [m.id for m in matches]

    judge_result = {}
    
    # 3. Stage 2: Call the LLM judge if the output clears the similarity threshold
    if top_similarity >= settings.SIMILARITY_THRESHOLD and matches:
        matched_texts = [m.text for m in matches]
        
        for attempt in range(2):
            try:
                judge_result = await judge_factual_overlap(payload.output_text, matched_texts)
                break
            except Exception as e:
                print(f"Judge call failed (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    await asyncio.sleep(0.5)
                else:
                    judge_result = {"verdict": "judge_unavailable"}

    # 4. Log the scored output for audit and future processing
    scored = ScoredOutput(
        agent_id=payload.agent_id,
        session_id=payload.session_id,
        output_text=payload.output_text,
        similarity_score=top_similarity,
        matched_chunk_ids=matched_ids,
        judge_verdict=judge_result.get("verdict"),
        judge_confidence=judge_result.get("confidence"),
        matched_facts=judge_result.get("matched_facts"),
    )
    session.add(scored)
    await session.commit()

    response_data = {
        "scored_output_id": scored.id,
        "similarity_score": top_similarity,
        "matched_chunks": [{"id": m.id, "text": m.text[:200], "similarity": m.similarity} for m in matches],
    }
    
    if judge_result:
        response_data["judge_verdict"] = judge_result.get("verdict")
        if "confidence" in judge_result:
            response_data["judge_confidence"] = judge_result.get("confidence")
        if "reason" in judge_result:
            response_data["judge_reason"] = judge_result.get("reason")
            
    return response_data

from sqlalchemy import select
@router.get("/debug/scored_outputs")
async def get_scored_outputs(session: AsyncSession = Depends(get_session)):
    stmt = select(ScoredOutput).where(ScoredOutput.judge_verdict == 'leak').order_by(ScoredOutput.id.desc()).limit(2)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "output_text": r.output_text[:50] + "...",
            "judge_verdict": r.judge_verdict,
            "judge_confidence": r.judge_confidence,
            "matched_facts": r.matched_facts
        }
        for r in rows
    ]
