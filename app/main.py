"""
AegisAI — FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import engine, Base
from prometheus_fastapi_instrumentator import Instrumentator
from app.routers import health, vault, score, eval

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (pgvector extension must already exist)."""
    async with engine.begin() as conn:
        await conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Import models so Base.metadata knows about them
        import app.models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="AI-powered cybersecurity detection platform",
    lifespan=lifespan,
)

Instrumentator().instrument(app).expose(app)

app.include_router(health.router)
app.include_router(vault.router)
app.include_router(score.router)
app.include_router(eval.router)
