"""
app/schemas/analytics.py

Pydantic schemas for Phase 8 — Analytics & Performance Tracking.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

class AnalyticsOverview(BaseModel):
    total_interviews: int
    completed_interviews: int
    evaluated_interviews: int
    average_score: Optional[float]
    best_score: Optional[int]
    lowest_score: Optional[int]
    latest_score: Optional[int]


# ---------------------------------------------------------------------------
# Score Trend
# ---------------------------------------------------------------------------

class ScoreTrendItem(BaseModel):
    interview_id: str
    title: str
    date: datetime
    score: int


class ScoreTrendResponse(BaseModel):
    data: List[ScoreTrendItem]


# ---------------------------------------------------------------------------
# Category Performance
# ---------------------------------------------------------------------------

class CategoryPerformance(BaseModel):
    technical: Optional[float]
    communication: Optional[float]
    problem_solving: Optional[float]
    relevance: Optional[float]


# ---------------------------------------------------------------------------
# Topic Performance
# ---------------------------------------------------------------------------

class TopicPerformance(BaseModel):
    topic: str
    average_score: float
    interviews_count: int


class TopicPerformanceResponse(BaseModel):
    topics: List[TopicPerformance]


# ---------------------------------------------------------------------------
# Strengths & Weaknesses
# ---------------------------------------------------------------------------

class StrengthItem(BaseModel):
    text: str
    count: int


class StrengthsResponse(BaseModel):
    strengths: List[StrengthItem]


class WeaknessItem(BaseModel):
    text: str
    count: int


class WeaknessesResponse(BaseModel):
    weaknesses: List[WeaknessItem]


# ---------------------------------------------------------------------------
# Interview History
# ---------------------------------------------------------------------------

class InterviewHistoryItem(BaseModel):
    interview_id: str
    title: str
    role: str
    interview_type: str
    difficulty: str
    score: Optional[int]
    date: Optional[datetime]


class InterviewHistoryResponse(BaseModel):
    items: List[InterviewHistoryItem]
    page: int
    limit: int
    total: int


# ---------------------------------------------------------------------------
# Interview Type Performance
# ---------------------------------------------------------------------------

class InterviewTypePerformance(BaseModel):
    type: str
    average_score: float
    count: int


class InterviewTypeResponse(BaseModel):
    data: List[InterviewTypePerformance]


# ---------------------------------------------------------------------------
# Difficulty Performance
# ---------------------------------------------------------------------------

class DifficultyPerformance(BaseModel):
    difficulty: str
    average_score: float
    count: int


class DifficultyResponse(BaseModel):
    data: List[DifficultyPerformance]


# ---------------------------------------------------------------------------
# Role Performance
# ---------------------------------------------------------------------------

class RolePerformance(BaseModel):
    role: str
    average_score: float
    count: int


class RoleResponse(BaseModel):
    data: List[RolePerformance]


# ---------------------------------------------------------------------------
# Improvement Analysis
# ---------------------------------------------------------------------------

class ImprovementAnalysis(BaseModel):
    """
    Compares performance in the earlier half of interviews vs the recent half.
    trend: "improving" | "declining" | "stable" | "insufficient_data"
    """
    previous_average: Optional[float]
    recent_average: Optional[float]
    score_difference: Optional[float]
    improvement_percentage: Optional[float]
    trend: str


# ---------------------------------------------------------------------------
# Full Analytics (dashboard endpoint)
# ---------------------------------------------------------------------------

class FullAnalyticsResponse(BaseModel):
    overview: AnalyticsOverview
    score_trend: List[ScoreTrendItem]
    category_performance: CategoryPerformance
    top_topics: List[TopicPerformance]
    top_strengths: List[StrengthItem]
    top_weaknesses: List[WeaknessItem]
    improvement: ImprovementAnalysis
