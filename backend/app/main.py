"""
app/main.py

FastAPI application entry point for the PrepAI backend.
Phase 1: Basic server + health check + MongoDB connection.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.routes.health import router as health_router
from app.routes.auth import router as auth_router
from app.routes.interviews import router as interviews_router
from app.routes.ai import router as ai_router
from app.routes.resume import router as resume_router
from app.routes.feedback import router as feedback_router
from app.routes.analytics import router as analytics_router
from app.routes.voice import router as voice_router
from app.routes.agents import router as agents_router  # Phase 10

# Create the FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Mock Interview & Career Preparation Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    # Serialize response models using field names (e.g. "id") not aliases (e.g. "_id")
    # This ensures all PyObjectId fields named "id" appear as "id" in API responses
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Register Routers ---
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(interviews_router)
app.include_router(ai_router)
app.include_router(resume_router)
app.include_router(feedback_router)
app.include_router(analytics_router)
app.include_router(voice_router)
app.include_router(agents_router)  # Phase 10 — Agentic AI


# --- Root Endpoint ---
@app.get("/", tags=["Root"])
def root():
    """Root endpoint — quick confirmation the server is running."""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }
