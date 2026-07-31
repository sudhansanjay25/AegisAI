"""
Scoring router — evaluates an LLM output against the vault.
"""

import asyncio
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.ingestion.embed import embed_batch
from app.detection.similarity import find_similar_chunks
from app.detection.judge import judge_factual_overlap
from app.detection.policy import compute_risk_score, route_policy
from app.models import ScoredOutput
from app.config import settings
from app.auth import verify_api_key
from prometheus_client import Counter, Histogram

router = APIRouter(tags=["scoring"])

REQUESTS_SCORED_TOTAL = Counter("requests_scored_total", "Total scoring requests processed")
POLICY_ACTIONS_TOTAL = Counter("policy_actions_total", "Total policy actions triggered", ["action"])
JUDGE_LATENCY_SECONDS = Histogram("judge_latency_seconds", "Latency of LLM judge calls")
JUDGE_ERRORS_TOTAL = Counter("judge_errors_total", "Total errors from the LLM judge")


class ScoreRequest(BaseModel):
    output_text: str
    agent_id: str | None = None
    session_id: str | None = None


@router.post("/v1/outputs/score", dependencies=[Depends(verify_api_key)])
async def score_output(
    payload: ScoreRequest, 
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    """Score an incoming LLM output against the vault using cosine similarity and LLM judge."""
    
    # 1. Embed the incoming output text
    import time
    t0 = time.time()
    [embedding] = embed_batch([payload.output_text])
    
    # 2. Find the closest matching chunks in the vault
    matches = await find_similar_chunks(session, embedding, top_k=5)

    # Use the highest similarity score (the first match) as the overall score
    top_similarity = matches[0].similarity if matches else 0.0
    matched_ids = [m.id for m in matches]

    judge_result = {}
    
    t1 = time.time()
    print(f"[LATENCY] Stage 1 (Embedding + DB Search) took: {t1 - t0:.3f}s")
    
    # 3. Stage 2: Call the LLM judge if the output clears the similarity threshold
    if top_similarity >= settings.SIMILARITY_THRESHOLD and matches:
        matched_texts = [m.text for m in matches]
        
        for attempt in range(2):
            try:
                start_time = time.time()
                judge_result = await judge_factual_overlap(payload.output_text, matched_texts)
                JUDGE_LATENCY_SECONDS.observe(time.time() - start_time)
                break
            except Exception as e:
                JUDGE_ERRORS_TOTAL.inc()
                print(f"Judge call failed (attempt {attempt + 1}): {e}")
                if attempt == 0:
                    await asyncio.sleep(0.5)
                else:
                    judge_result = {"verdict": "judge_unavailable", "reason": str(e)}

    t2 = time.time()
    print(f"[LATENCY] Stage 2 (Groq LLM Call) took: {t2 - t1:.3f}s")

    # 4. Stage 3: Risk Aggregation & Policy Routing
    risk_score = compute_risk_score(
        top_similarity, 
        judge_result.get("verdict"), 
        judge_result.get("confidence"),
        judge_result.get("matched_facts")
    )
    policy_action = route_policy(risk_score)
    POLICY_ACTIONS_TOTAL.labels(action=policy_action).inc()
    REQUESTS_SCORED_TOTAL.inc()

    # 5. Log the scored output for audit and future processing
    scored = ScoredOutput(
        agent_id=payload.agent_id,
        session_id=payload.session_id,
        output_text=payload.output_text,
        similarity_score=top_similarity,
        matched_chunk_ids=matched_ids,
        judge_verdict=judge_result.get("verdict"),
        judge_confidence=judge_result.get("confidence"),
        matched_facts=judge_result.get("matched_facts"),
        judge_model_used=judge_result.get("judge_model_used"),
        risk_score=risk_score,
        policy_action=policy_action,
    )
    session.add(scored)
    await session.commit()

    response_data = {
        "scored_output_id": scored.id,
        "similarity_score": top_similarity,
        "risk_score": risk_score,
        "policy_action": policy_action,
        "matched_chunks": [{"id": m.id, "document": m.document_title, "text": m.text[:200], "similarity": m.similarity} for m in matches],
    }
    
    if judge_result:
        response_data["judge_verdict"] = judge_result.get("verdict")
        if "confidence" in judge_result:
            response_data["judge_confidence"] = judge_result.get("confidence")
            
        # Explainability
        if judge_result.get("verdict") == "judge_unavailable":
            response_data["explainability"] = {
                "reason": judge_result.get("reason")
            }
        else:
            response_data["explainability"] = {}
            if "judge_model_used" in judge_result:
                response_data["explainability"]["judge_model_used"] = judge_result.get("judge_model_used")
            if matches:
                response_data["explainability"]["matched_document"] = matches[0].document_title
            if "matched_facts" in judge_result:
                response_data["explainability"]["matched_facts"] = judge_result.get("matched_facts")
            if "reason" in judge_result:
                response_data["explainability"]["reason"] = judge_result.get("reason")
            
    if policy_action in ("block", "human_review"):
        background_tasks.add_task(trigger_webhook, response_data)
        
    return response_data

from fastapi import HTTPException
from sqlalchemy import select
from datetime import date
import httpx

@router.get("/v1/outputs/{output_id}", dependencies=[Depends(verify_api_key)])
async def get_output(output_id: int, session: AsyncSession = Depends(get_session)):
    stmt = select(ScoredOutput).where(ScoredOutput.id == output_id)
    result = await session.execute(stmt)
    scored = result.scalar_one_or_none()
    if not scored:
        raise HTTPException(status_code=404, detail="Scored output not found")
    return scored

@router.get("/v1/alerts", dependencies=[Depends(verify_api_key)])
async def get_alerts(
    agent_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    session: AsyncSession = Depends(get_session)
):
    stmt = select(ScoredOutput).where(ScoredOutput.policy_action.in_(["block", "human_review"]))
    if agent_id:
        stmt = stmt.where(ScoredOutput.agent_id == agent_id)
    if start_date:
        stmt = stmt.where(ScoredOutput.created_at >= start_date)
    if end_date:
        stmt = stmt.where(ScoredOutput.created_at <= end_date)
    
    stmt = stmt.order_by(ScoredOutput.id.desc()).limit(100)
    result = await session.execute(stmt)
    return result.scalars().all()

async def trigger_webhook(payload: dict):
    if not settings.WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                settings.WEBHOOK_URL, 
                json={"text": f"🚨 AegisAI Alert: {payload['policy_action'].upper()} on agent {payload.get('agent_id', 'unknown')}. Risk Score: {payload['risk_score']:.1f}"},
                timeout=5.0
            )
    except Exception as e:
        print(f"Webhook failed: {e}")
