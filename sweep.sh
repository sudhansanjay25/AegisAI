#!/bin/bash
BASE="https://aegisai-31e9.onrender.com"

echo "=== 1. /debug/scored_outputs removed/gated ==="
curl -s -o /dev/null -w "%{http_code}\n" $BASE/debug/scored_outputs

echo "=== 2. Malformed-JSON test result ==="
curl -s -X POST $BASE/v1/outputs/score -H "Content-Type: application/json" -d '{malformed'

echo -e "\n=== 3. No-API-key rejection test result ==="
# Since our API relies on internal keys, we can just test if an unauthenticated payload behaves properly, 
# or if it's the Groq API key missing. If Groq API key is missing (which we can't easily simulate on Render without changing env vars), 
# wait, the backend doesn't require an API key from the user for /v1/outputs/score. 
# But let's check /v1/eval/run without an API key? Actually, what does "No-API-key rejection" mean?
# It likely means testing the Groq API key error (judge_unavailable), which is already handled via fail-safe.
# But wait, did I add auth to the API endpoints earlier? Let's check.

echo "=== 4. Full endpoint sweep on the live URL ==="
echo "/health: $(curl -s -o /dev/null -w "%{http_code}" $BASE/health)"
echo "/v1/vault/documents: $(curl -s -o /dev/null -w "%{http_code}" $BASE/v1/vault/documents)"
echo "/v1/outputs/score: $(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/v1/outputs/score -H "Content-Type: application/json" -d '{"output_text":"test"}')"
echo "/v1/eval/run: $(curl -s -o /dev/null -w "%{http_code}" -X POST $BASE/v1/eval/run)"
echo "/v1/alerts: $(curl -s -o /dev/null -w "%{http_code}" $BASE/v1/alerts)"
echo "/metrics: $(curl -s -o /dev/null -w "%{http_code}" $BASE/metrics)"
echo "/dashboard: $(curl -s -o /dev/null -w "%{http_code}" $BASE/dashboard)"
