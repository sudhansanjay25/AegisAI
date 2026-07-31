"""
Hour 19-21: Server-rendered dashboard.

Drop this file into app/routers/dashboard.py (adjust the import path for
your ScoredOutput model / get_session dependency to match your actual
project layout — the field names below match what's described in the
handoff doc: risk_score, policy_action, judge_verdict, created_at, and the
explainability fields matched_document / matched_facts / reason).

Wire into your main FastAPI app with:

    from app.routers import dashboard
    app.include_router(dashboard.router)

and make sure Jinja2Templates points at app/templates (see note at bottom
of this file re: static file serving on Render).
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ADJUST: import your actual model + session dependency
from app.models import ScoredOutput
from app.db import get_session

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

# Policy action -> color mapping used by the template
POLICY_COLORS = {
    "allow": "#2e7d32",         # green
    "redact": "#e6a817",        # amber
    "human_review": "#e07b00",  # orange
    "block": "#c62828",         # red
}

# Simple fixed buckets for the plain bar-style score distribution.
# No charting library — per the Hour 19-21 plan, this is just counts
# per 0-100 bucket rendered as CSS width bars in the template.
SCORE_BUCKETS = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ScoredOutput).order_by(ScoredOutput.created_at.desc()).limit(20)
    )
    rows = result.scalars().all()

    # Build the bar-distribution counts from these same 20 rows.
    # (If you'd rather distribution reflect ALL scored outputs rather than
    # just the last 20 shown in the table, swap this for a separate
    # unbounded query — the plan doesn't specify which, so this defaults
    # to "same 20 rows the table shows" for consistency between the two
    # panels. Document whichever you pick as a one-line judgment call.)
    bucket_counts = []
    for lo, hi in SCORE_BUCKETS:
        count = sum(1 for r in rows if lo <= r.risk_score < hi)
        bucket_counts.append({"label": f"{lo}-{hi-1}", "count": count})
    max_count = max((b["count"] for b in bucket_counts), default=0) or 1

    from app.config import settings
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "rows": rows,
            "policy_colors": POLICY_COLORS,
            "bucket_counts": bucket_counts,
            "max_count": max_count,
            "api_key": settings.API_KEY,
        },
    )


# --- Static file serving note (per Hour 19-21 plan: "confirm this works
# under Render, not just local — this build has hit works-locally/
# breaks-on-deploy twice already") ---
#
# This template uses inline CSS (no external static assets), which
# sidesteps the static-file-serving risk entirely for the dashboard
# itself. If you DO add a separate static/ dir later (e.g. a favicon or
# a JS file instead of inline <script>), mount it in your main app as:
#
#     from fastapi.staticfiles import StaticFiles
#     app.mount("/static", StaticFiles(directory="app/static"), name="static")
#
# and verify with a live curl against the Render URL, not just localhost —
# Render's filesystem/working-directory behavior at container start has
# already bitten this build once (vault seed) and been the source of a
# second near-miss (eval endpoint).
