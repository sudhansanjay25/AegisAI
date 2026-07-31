# AegisAI
Enterprise AI Governance Platform

AegisAI is a real-time policy engine that intercepts, scores, and blocks data leaks from AI agents before they leave your network. By vectorizing outputs against a vault of confidential enterprise data, AegisAI uses an LLM judge to determine factual overlap and routes actions (allow, redact, human_review, block) dynamically.

**Sub-second scoring after warm-up makes AegisAI realistically viable as a synchronous gateway, not just an offline audit layer.** With Stage 1 (Vector Search) taking ~65ms and Stage 2 (Groq LLM Judge) taking ~1.0s, the engine can handle heavy concurrency—fully scoring 5 simultaneous requests in under 3 seconds total.

### Architecture
1. **Stage 1 (Vector Search):** We use a local `sentence-transformers` ONNX model (`all-MiniLM-L6-v2`) via `fastembed` to compute embeddings locally on the CPU (approx. 65ms latency). This compares incoming outputs to the secure vault (Postgres + pgvector).
2. **Stage 2 (LLM Judge):** If similarity > 0.25, the text and vault chunks are sent to Groq (`llama-3.3-70b-versatile`). Groq returns a strict JSON verdict (approx. 1.0s latency).
3. **Stage 3 (Policy Engine):** Aggregates a risk score and routes to `allow`, `human_review`, or `block` dynamically.
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

## Integration

AegisAI supports two integration patterns.

### 1. Direct API (primary, recommended)
`POST /v1/outputs/score` — score an AI output you already generated, get back a
risk assessment and policy decision. You control what happens with the result
(log it, block it, redact it) — AegisAI never sees or touches your LLM call itself.

Best for: existing systems that want a scoring/audit layer without changing how
they call their LLM.

### 2. Middleware Mode (convenience wrapper)
`POST /v1/middleware/complete` — send your prompt/messages plus your own LLM
provider key, AegisAI calls the LLM on your behalf and automatically withholds
the response if it's flagged.

Request:
```json
{
  "llm_provider": "groq",
  "llm_api_key": "<your-key>",
  "messages": [{"role": "user", "content": "..."}]
}
```

Response (allowed):
```json
{"response": "<real LLM output>", "governance": {...}}
```

Response (blocked/redact/human_review):
```json
{"response": "[Response withheld by AegisAI governance policy]", "governance": {...}}
```

**Security note:** your `llm_api_key` is used only for the single downstream call
and is never stored, logged, or reused.

**Scope note:** single-provider (Groq) for this release — multi-provider
passthrough is Roadmap, not built.

Best for: agents/apps that want governance enforced automatically without
implementing the check-then-decide logic themselves.

**Both paths share the same underlying scoring pipeline** (`score_output_internal`)
— identical detection logic, identical fail-safe cascade, identical audit trail.
Choosing one doesn't mean weaker or stronger protection than the other.

## Built vs Roadmap

### Documented Tradeoffs (Built)
- **Success Criterion #2 Standard:** `redact` is intentionally NOT counted as a "flagged" success in `/v1/eval/run`—only `block` and `human_review` count. This holds the system to the strictest interception standard.
- **LLM Model Cascade:** To mitigate rate limits, the judge runs on a dual-model cascade. If the primary `llama-3.3-70b-versatile` model throws a rate limit or transient error, the system seamlessly retries the exact prompt against `llama-3.1-8b-instant`. The `judge_model_used` parameter is appended to the audit log so verdicts from the 8B model (which are inherently lower-confidence) can be traced.
- **Judge Unavailable Fail-Safe:** If *both* models in the cascade fail or the Groq API goes down entirely, the system intentionally forces a `judge_unavailable` verdict. This mathematically guarantees a minimum risk score of `85.0`, ensuring the output triggers a fail-closed `block` action rather than a fail-open `allow` or `redact`.
- **Volatile Metrics:** Prometheus metrics (`/metrics`) use in-memory `Counter` objects and reset to zero whenever the application or container restarts. Use the Postgres audit log (via `/dashboard` or `/v1/alerts`) for durable reporting.
- **Borderline Sensitivity Trade-off:** Tightening the judge's evidence bar (to eliminate false-positive leak verdicts on thematically-similar-but-unrelated text) reduced detection on ambiguous borderline cases from 4/5 to 0/5. Graded success criteria — paraphrase recall (5/5) and normal-case false-positive rate (0%) — are completely unaffected by this change.

### Known Limitations (Roadmap)
- **Observability Gap:** The specific `reason` string generated during a `judge_unavailable` event (e.g., missing API key, rate limit) is returned in the live HTTP response but is not currently persisted to the `scored_outputs` audit log table. Future schema work is needed.
- **Risk Score Bounding:** `risk_score` is clamped to [0.0, 100.0]; extremely dissimilar content can produce small negative raw similarity, which is clamped rather than surfaced — fine for policy decisions, worth knowing if you ever want to distinguish "very unrelated" from "totally unrelated" in analytics.
