"""
AegisAI — FastAPI application entry point.
"""

from fastapi import FastAPI

from app.config import settings
from app.routers import health

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="AI-powered cybersecurity detection platform",
)

app.include_router(health.router)
