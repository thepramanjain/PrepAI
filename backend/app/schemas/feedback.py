"""
app/schemas/feedback.py

Pydantic schemas for Phase 7 — AI Interview Evaluation & Feedback.
"""

from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.schemas.user import PyObjectId


# ==========================================
# SCORE VALIDATION HELPER
# ==========================================

def _validate_score(v: int) -> int:
    if not (0 <= v <= 100):
        raise ValueError(f"Score must be between 0 and 100, got {v}")
    return v


# ==========================================
# SUB-SCHEMAS
# ==========================================

class CategoryScores(BaseModel):
    """Scores for each evaluation dimension (all 0–100)."""
    technical: int = Field(..., ge=0, le=100)
    communication: int = Field(..., ge=0, le=100)
    problem_solving: int = Field(..., ge=0, le=100)
    relevance: int = Field(..., ge=0, le=100)


class QuestionEvaluation(BaseModel):
    """Per-question evaluation referencing an actual question ID."""
    question_id: str
    score: int = Field(..., ge=0, le=100)
    quality: str = Field(..., min_length=1)
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)
    feedback: str = Field(..., min_length=1)


class TopicAnalysis(BaseModel):
    """Topic-level performance derived from question categories."""
    topic: str = Field(..., min_length=1)
    score: int = Field(..., ge=0, le=100)
    assessment: Literal["Weak", "Needs Improvement", "Average", "Good", "Strong", "Excellent"]


# ==========================================
# GEMINI OUTPUT VALIDATION
# ==========================================

class GeneratedEvaluation(BaseModel):
    """
    Pydantic schema used to validate raw Gemini JSON output.
    Strict score validation ensures Gemini cannot return out-of-range scores.
    """
    overall_score: int = Field(..., ge=0, le=100)
    category_scores: CategoryScores
    question_evaluations: List[QuestionEvaluation]
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    topic_analysis: List[TopicAnalysis] = Field(default_factory=list)
    summary: str = Field(..., min_length=10)


# ==========================================
# API RESPONSE SCHEMAS
# ==========================================

class FeedbackResponse(BaseModel):
    """
    Full feedback document returned to the client.
    MongoDB ObjectIds are serialized to strings.
    """
    id: PyObjectId = Field(validation_alias="_id")
    interview_id: PyObjectId
    user_id: PyObjectId
    overall_score: int
    category_scores: CategoryScores
    question_evaluations: List[QuestionEvaluation]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    topic_analysis: List[TopicAnalysis]
    summary: str
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True, "arbitrary_types_allowed": True}
