"""
app/routes/analytics.py

Phase 8 — Analytics & Performance Tracking API routes.

All endpoints:
  - Require JWT authentication
  - Derive user identity from the token (never from request body)
  - Delegate all business logic to analytics_service

Date filtering:
  - ?days=7 | 30 | 90 | 365
  - Omit for all-time history
  - Invalid values return HTTP 400
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from app.schemas.analytics import (
    AnalyticsOverview,
    ScoreTrendResponse,
    CategoryPerformance,
    TopicPerformanceResponse,
    StrengthsResponse,
    WeaknessesResponse,
    InterviewHistoryResponse,
    InterviewTypeResponse,
    DifficultyResponse,
    RoleResponse,
    ImprovementAnalysis,
    FullAnalyticsResponse,
)
from app.services import analytics_service
from app.routes.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# Allowed values for the ?days query parameter
_VALID_DAYS = {7, 30, 90, 365}


def _validate_days(days: Optional[int]) -> None:
    """Raise HTTP 400 if days is provided but not one of the allowed values."""
    if days is not None and days not in _VALID_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid 'days' value: {days}. Allowed: {sorted(_VALID_DAYS)}",
        )


# ---------------------------------------------------------------------------
# GET /api/analytics  — Full dashboard payload
# ---------------------------------------------------------------------------

@router.get("", response_model=FullAnalyticsResponse, summary="Full analytics dashboard")
def full_analytics(
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Consolidated analytics endpoint returning all key metrics in a single call.
    Designed to power the frontend dashboard with one request.
    """
    _validate_days(days)
    return analytics_service.get_full_analytics(str(current_user["_id"]), days)


# ---------------------------------------------------------------------------
# GET /api/analytics/overview
# ---------------------------------------------------------------------------

@router.get("/overview", response_model=AnalyticsOverview, summary="Overview statistics")
def overview(
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns aggregate interview counts and score summary.
    Scores are null when no evaluated interviews exist.
    """
    _validate_days(days)
    return analytics_service.get_overview(str(current_user["_id"]), days)


# ---------------------------------------------------------------------------
# GET /api/analytics/score-trend
# ---------------------------------------------------------------------------

@router.get("/score-trend", response_model=ScoreTrendResponse, summary="Score trend over time")
def score_trend(
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns chronological (oldest → newest) interview scores.
    Use this data to render a line chart in the frontend.
    """
    _validate_days(days)
    data = analytics_service.get_score_trend(str(current_user["_id"]), days)
    return {"data": data}


# ---------------------------------------------------------------------------
# GET /api/analytics/categories
# ---------------------------------------------------------------------------

@router.get("/categories", response_model=CategoryPerformance, summary="Category performance averages")
def categories(
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns average scores for the four Phase 7 evaluation categories:
    technical, communication, problem_solving, relevance.
    Null when no evaluated interviews exist.
    """
    _validate_days(days)
    return analytics_service.get_category_performance(str(current_user["_id"]), days)


# ---------------------------------------------------------------------------
# GET /api/analytics/topics
# ---------------------------------------------------------------------------

@router.get("/topics", response_model=TopicPerformanceResponse, summary="Topic performance")
def topics(
    limit: int = Query(20, ge=1, le=20, description="Maximum topics to return (1–20)"),
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Aggregates topic_analysis from Phase 7 feedback across all interviews.
    Returns topics sorted by average score descending.
    """
    _validate_days(days)
    data = analytics_service.get_topic_performance(str(current_user["_id"]), days, limit)
    return {"topics": data}


# ---------------------------------------------------------------------------
# GET /api/analytics/strengths
# ---------------------------------------------------------------------------

@router.get("/strengths", response_model=StrengthsResponse, summary="Recurring strengths")
def strengths(
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Aggregates and counts strength strings from Phase 7 feedback.
    Normalized to lowercase for counting; original case preserved for display.
    Sorted by frequency descending.
    """
    _validate_days(days)
    data = analytics_service.get_strengths(str(current_user["_id"]), days)
    return {"strengths": data}


# ---------------------------------------------------------------------------
# GET /api/analytics/weaknesses
# ---------------------------------------------------------------------------

@router.get("/weaknesses", response_model=WeaknessesResponse, summary="Recurring weaknesses")
def weaknesses(
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Aggregates and counts weakness strings from Phase 7 feedback.
    Sorted by frequency descending.
    """
    _validate_days(days)
    data = analytics_service.get_weaknesses(str(current_user["_id"]), days)
    return {"weaknesses": data}


# ---------------------------------------------------------------------------
# GET /api/analytics/history
# ---------------------------------------------------------------------------

@router.get("/history", response_model=InterviewHistoryResponse, summary="Paginated interview history")
def history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(10, ge=1, le=50, description="Items per page (1–50)"),
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns a paginated list of completed interviews, newest first.
    Score is null if the interview has not yet been evaluated.
    """
    _validate_days(days)
    return analytics_service.get_history(str(current_user["_id"]), page, limit, days)


# ---------------------------------------------------------------------------
# GET /api/analytics/interview-types
# ---------------------------------------------------------------------------

@router.get(
    "/interview-types",
    response_model=InterviewTypeResponse,
    summary="Performance by interview type",
)
def interview_types(
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns average score and count grouped by interview type
    (Technical, Behavioral, HR, etc.).
    """
    _validate_days(days)
    data = analytics_service.get_interview_type_performance(str(current_user["_id"]), days)
    return {"data": data}


# ---------------------------------------------------------------------------
# GET /api/analytics/difficulty
# ---------------------------------------------------------------------------

@router.get("/difficulty", response_model=DifficultyResponse, summary="Performance by difficulty level")
def difficulty(
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns average score and count grouped by difficulty level.
    Only returns levels for which evaluated data exists.
    """
    _validate_days(days)
    data = analytics_service.get_difficulty_performance(str(current_user["_id"]), days)
    return {"data": data}


# ---------------------------------------------------------------------------
# GET /api/analytics/roles
# ---------------------------------------------------------------------------

@router.get("/roles", response_model=RoleResponse, summary="Performance by job role")
def roles(
    days: Optional[int] = Query(None, description="Filter to last N days (7, 30, 90, 365)"),
    current_user: dict = Depends(get_current_user),
):
    """
    Returns average score and count grouped by job role.
    """
    _validate_days(days)
    data = analytics_service.get_role_performance(str(current_user["_id"]), days)
    return {"data": data}


# ---------------------------------------------------------------------------
# GET /api/analytics/improvement
# ---------------------------------------------------------------------------

@router.get("/improvement", response_model=ImprovementAnalysis, summary="Improvement trend analysis")
def improvement(
    current_user: dict = Depends(get_current_user),
):
    """
    Compares the user's earlier interview scores vs recent scores.
    Uses all available history (no date filter) for a meaningful trend.

    Requires ≥2 evaluated interviews; returns trend="insufficient_data" otherwise.
    trend values: "improving" | "declining" | "stable" | "insufficient_data"
    """
    return analytics_service.get_improvement(str(current_user["_id"]))
