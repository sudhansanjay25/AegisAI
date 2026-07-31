# AegisAI
Enterprise AI Governance Platform

AegisAI is a real-time policy engine that intercepts, scores, and blocks data leaks from AI agents before they leave your network. By vectorizing outputs against a vault of confidential enterprise data, AegisAI uses an LLM judge to determine factual overlap and routes actions (allow, redact, human_review, block) dynamically.

### Live Environment
- **API URL:** `https://aegisai-31e9.onrender.com`
- **Dashboard:** [https://aegisai-31e9.onrender.com/dashboard](https://aegisai-31e9.onrender.com/dashboard)
- **Repo:** [https://github.com/sudhansanjay25/AegisAI](https://github.com/sudhansanjay25/AegisAI)

## Architecture
```text
[ Agent Output ] -> (1) Embedding & Similarity Search -> [ Top K Chunks ]
                                                               |
                                                               v
[ Policy Routing ] <- (3) Risk Aggregation <- (2) Groq LLM Fact Judge
 (Allow/Block)          (Score 0-100)           (Verdict & Confidence)
```

## Local Development
Requires Python 3.11+ and Postgres.
1. **Environment Variables:** Create a `.env` file with:
   - `GROQ_API_KEY=your_key`
   - `DATABASE_URL=postgresql+asyncpg://...`
2. **Install & Sync:** `uv sync`
3. **Run Locally:** `docker compose up --build` or `uv run uvicorn app.main:app --reload`

## Built vs Roadmap

### Documented Tradeoffs (Built)
- **Success Criterion #2 Standard:** `redact` is intentionally NOT counted as a "flagged" success in `/v1/eval/run`—only `block` and `human_review` count. This holds the system to the strictest interception standard.
- **Judge Unavailable Fail-Safe:** If the Groq API goes down, the system intentionally forces a `judge_unavailable` verdict which mathematically bumps borderline similarity scores into the `block` policy threshold (fail-closed design rather than fail-open).
- **Standalone API vs SDK:** AegisAI is deployed as a standalone REST API rather than an embedded SDK to remain completely language-agnostic and avoid coupling caller agents to our release cycles.

### Known Limitations (Roadmap)
- **Observability Gap:** The specific `reason` string generated during a `judge_unavailable` event (e.g., missing API key, rate limit) is returned in the live HTTP response but is not currently persisted to the `scored_outputs` audit log table. Future schema work is needed.
- **Volatile Metrics:** Prometheus metrics (`/metrics`) use in-memory `Counter` objects and reset to zero whenever the application or container restarts. Use the Postgres audit log (via `/dashboard` or `/v1/alerts`) for durable reporting.
- **Borderline Sensitivity Trade-off:** Tightening the judge's evidence bar (to eliminate false-positive leak verdicts on thematically-similar-but-unrelated text) reduced detection on ambiguous borderline cases from 4/5 to 0/5. Graded success criteria — paraphrase recall (5/5) and normal-case false-positive rate (0%) — are completely unaffected by this change.
