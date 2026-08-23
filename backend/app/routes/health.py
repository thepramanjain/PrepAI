"""
app/routes/health.py

Health check endpoints for the PrepAI backend.
- GET /api/health      — basic application health
- GET /api/health/db   — MongoDB connectivity check
"""

from fastapi import APIRouter, HTTPException

from app.config.database import test_connection
from app.config.settings import settings

router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("")
def health_check():
    """Basic health check — confirms the API is running."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@router.get("/db")
def health_check_db():
    """
    Database health check — pings MongoDB to verify connectivity.
    Returns 503 Service Unavailable if the database is unreachable.
    """
    try:
        test_connection()
        return {
            "status": "ok",
            "database": "connected",
        }
    except ConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "database": "disconnected",
                "message": str(e),
            },
        )
