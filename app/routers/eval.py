import json
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.ingestion.embed import embed_batch
from app.detection.similarity import find_similar_chunks
from app.detection.judge import judge_factual_overlap
from app.detection.policy import compute_risk_score, route_policy
from app.config import settings

router = APIRouter(tags=["eval"])

@router.post("/v1/eval/run")
async def run_evaluation(session: AsyncSession = Depends(get_session)):
    with open("tests/eval_cases.json") as f:
        cases = json.load(f)
        
    results = {
        "total_cases": len(cases),
        "true_positives": 0,
        "false_positives": 0,
        "true_negatives": 0,
        "false_negatives": 0,
        "precision": 0.0,
        "recall": 0.0,
        "false_positive_rate": 0.0,
        "details": []
    }
    
    for case in cases:
        [embedding] = embed_batch([case["text"]])
        matches = await find_similar_chunks(session, embedding, top_k=5)
        top_similarity = matches[0].similarity if matches else 0.0
        
        judge_result = {}
        if top_similarity >= settings.SIMILARITY_THRESHOLD and matches:
            matched_texts = [m.text for m in matches]
            try:
                judge_result = await judge_factual_overlap(case["text"], matched_texts)
            except Exception:
                judge_result = {"verdict": "judge_unavailable"}
                
        risk_score = compute_risk_score(
            top_similarity,
            judge_result.get("verdict"),
            judge_result.get("confidence")
        )
        policy_action = route_policy(risk_score)
        
        is_positive_prediction = policy_action in ("block", "human_review")
        is_positive_actual = case["label"] in ("paraphrase", "borderline")
        
        if is_positive_prediction and is_positive_actual:
            results["true_positives"] += 1
        elif is_positive_prediction and not is_positive_actual:
            results["false_positives"] += 1
        elif not is_positive_prediction and not is_positive_actual:
            results["true_negatives"] += 1
        elif not is_positive_prediction and is_positive_actual:
            results["false_negatives"] += 1
            
        results["details"].append({
            "id": case["id"],
            "label": case["label"],
            "policy_action": policy_action,
            "risk_score": risk_score,
            "is_correct": is_positive_prediction == is_positive_actual
        })
        
    tp = results["true_positives"]
    fp = results["false_positives"]
    tn = results["true_negatives"]
    fn = results["false_negatives"]
    
    results["precision"] = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    results["recall"] = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    results["false_positive_rate"] = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    
    return results
