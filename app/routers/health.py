"""
Health-check router — readiness probe for the API and database.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    """
    Returns {"status": "ok", "db": "ok"} when the API can reach the database.
    Any unhandled DB error will bubble up as a 500 — that's intentional;
    a load-balancer should pull this instance out of rotation.
    """
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "ok"}
