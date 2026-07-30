"""
Scoring router — evaluates an LLM output against the vault.
"""

from pydantic import BaseModel
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ingestion.embed import embed_batch
from app.detection.similarity import find_similar_chunks
from app.models import ScoredOutput

router = APIRouter(tags=["scoring"])


class ScoreRequest(BaseModel):
    output_text: str
    agent_id: str | None = None
    session_id: str | None = None


@router.post("/v1/outputs/score")
async def score_output(payload: ScoreRequest, session: AsyncSession = Depends(get_session)):
    """Score an incoming LLM output against the vault using cosine similarity."""
    
    # 1. Embed the incoming output text
    [embedding] = embed_batch([payload.output_text])
    
    # 2. Find the closest matching chunks in the vault
    matches = await find_similar_chunks(session, embedding, top_k=5)

    # Use the highest similarity score (the first match) as the overall score
    top_similarity = matches[0].similarity if matches else 0.0
    matched_ids = [m.id for m in matches]

    # 3. Log the scored output for audit and future processing
    scored = ScoredOutput(
        agent_id=payload.agent_id,
        session_id=payload.session_id,
        output_text=payload.output_text,
        similarity_score=top_similarity,
        matched_chunk_ids=matched_ids,
    )
    session.add(scored)
    await session.commit()

    return {
        "scored_output_id": scored.id,
        "similarity_score": top_similarity,
        "matched_chunks": [{"id": m.id, "text": m.text[:200], "similarity": m.similarity} for m in matches],
    }
