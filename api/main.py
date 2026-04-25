"""
PromptWars LearnAI API — entry point.

Configures FastAPI app with CORS, routers, and startup/shutdown events.
"""

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.config import settings
from api.routers import auth, assistant, sessions, gamification
from api.utils.logging import get_logger

logger = get_logger(__name__)

# Path to the compiled React frontend (built by Dockerfile Stage 1 into /app/static)
STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


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
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://localhost:3000",
        "https://promptwars-api-596074253382.asia-south1.run.app",
    ],
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


# ── Serve Frontend SPA ────────────────────────────────────────────
# Mount /assets for Vite's chunked JS/CSS bundles
_assets_dir = os.path.join(STATIC_DIR, "assets")
if os.path.isdir(_assets_dir):
    app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str) -> FileResponse:
    """Serve the React SPA for all non-API routes (client-side routing support)."""
    # Try to serve a specific static file first (e.g. favicon.ico, vite.svg)
    candidate = os.path.join(STATIC_DIR, full_path)
    if full_path and os.path.isfile(candidate):
        return FileResponse(candidate)
    # Fall back to index.html for all SPA routes
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

