# AegisAI
Enterprise AI Governance Platform

## Known Limitations / Roadmap
- **Observability Gap:** The specific `reason` string generated during a `judge_unavailable` event (e.g., missing API key, rate limit, timeout) is returned in the live HTTP response but is not currently persisted to the `scored_outputs` audit log table. Future work should add this to the database schema so the dashboard/alerts can explicitly display why an outage occurred.
