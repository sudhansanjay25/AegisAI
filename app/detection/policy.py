def compute_risk_score(similarity_score: float, judge_verdict: str | None, judge_confidence: float | None, matched_facts: list[str] | None = None) -> float:
    if judge_verdict == "leak" and not matched_facts:
        judge_verdict = "no_leak"
        
    if judge_verdict == "leak":
        return min(100.0, 50.0 + float(judge_confidence or 0.0) * 50.0)
    if judge_verdict == "judge_unavailable":
        # Fail-closed: Guarantee at least a block (85.0+) if judge goes down
        return max(85.0, min(100.0, similarity_score * 160.0))
    return max(0.0, min(100.0, similarity_score * 40.0))

def route_policy(risk_score: float) -> str:
    if risk_score < 30: return "allow"
    if risk_score < 60: return "redact"
    if risk_score < 85: return "human_review"
    return "block"
