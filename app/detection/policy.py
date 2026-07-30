def compute_risk_score(similarity_score: float, judge_verdict: str | None, judge_confidence: float | None) -> float:
    if judge_verdict == "leak":
        return min(100.0, 50.0 + float(judge_confidence or 0.0) * 50.0)
    if judge_verdict == "judge_unavailable":
        return min(100.0, similarity_score * 160.0)
    return similarity_score * 40.0

def route_policy(risk_score: float) -> str:
    if risk_score < 30: return "allow"
    if risk_score < 60: return "redact"
    if risk_score < 85: return "human_review"
    return "block"
