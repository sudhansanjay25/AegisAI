#!/bin/bash
BASE="https://aegisai-31e9.onrender.com"
echo "=== 1. /health ==="
curl -s $BASE/health | jq || curl -s $BASE/health

echo -e "\n\n=== 2. /v1/vault/documents ==="
curl -s -X POST $BASE/v1/vault/documents -H "Content-Type: application/json" -d '{"text": "Test document", "document_title": "test.txt", "tags": []}' | jq

echo -e "\n\n=== 3. /v1/outputs/score ==="
curl -s -X POST $BASE/v1/outputs/score -H "Content-Type: application/json" -d '{"output_text": "One of our employees, Sarah Mitchell, lives at 1847 Oakwood Dr in San Jose."}' | jq

echo -e "\n\n=== 4. /v1/eval/run ==="
curl -s -X POST $BASE/v1/eval/run | jq '{precision, recall, true_positives, false_negatives}'

echo -e "\n\n=== 5. /v1/alerts ==="
curl -s $BASE/v1/alerts | jq '.[0]'

echo -e "\n\n=== 6. /v1/outputs/{id} ==="
curl -s $BASE/v1/outputs/1 | jq

echo -e "\n\n=== 7. /metrics ==="
curl -s $BASE/metrics | grep "requests_scored_total"

echo -e "\n\n=== 8. /dashboard ==="
curl -s -I $BASE/dashboard
