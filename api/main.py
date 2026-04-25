"""
PromptWars LearnAI API — entry point.

Configures FastAPI app with CORS, routers, and startup/shutdown events.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings
from api.routers import auth, assistant, sessions, gamification
from api.utils.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown events."""
    logger.info("LearnAI API starting up", extra={"project": settings.gcp_project_id})
    yield
    logger.info("LearnAI API shutting down")


app = FastAPI(
    title="LearnAI — Intelligent Learning Assistant",
    description="AI-powered adaptive learning with gamification",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(assistant.router)
app.include_router(sessions.router)
app.include_router(gamification.router)


# ── Health check (no auth required) ──────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check() -> dict:
    """Health check endpoint for Cloud Run."""
    return {"status": "ok", "service": "learnai", "project": settings.gcp_project_id}
