"""
app/schemas/interview.py

Pydantic schemas for interview management.
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum

from app.schemas.user import PyObjectId


class ExperienceLevel(str, Enum):
    fresher = "Fresher"
    zero_to_one = "0-1 years"
    one_to_three = "1-3 years"
    three_to_five = "3-5 years"
    five_plus = "5+ years"

class InterviewType(str, Enum):
    technical = "Technical"
    hr = "HR"
    behavioral = "Behavioral"
    dsa = "DSA"
    system_design = "System Design"
    ai_ml = "AI/ML"
    frontend = "Frontend"
    backend = "Backend"
    full_stack = "Full Stack"
    mixed = "Mixed"

class Difficulty(str, Enum):
    easy = "Easy"
    medium = "Medium"
    hard = "Hard"
    expert = "Expert"

class Mode(str, Enum):
    text = "text"
    voice = "voice"

class Status(str, Enum):
    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"


class InterviewCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., min_length=1, max_length=100)
    experience_level: ExperienceLevel
    skills: List[str] = Field(..., min_length=1)
    interview_type: InterviewType
    difficulty: Difficulty
    job_description: Optional[str] = None
    mode: Mode
    resume_id: Optional[str] = None


class InterviewUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[str] = Field(None, min_length=1, max_length=100)
    experience_level: Optional[ExperienceLevel] = None
    skills: Optional[List[str]] = None
    interview_type: Optional[InterviewType] = None
    difficulty: Optional[Difficulty] = None
    job_description: Optional[str] = None
    mode: Optional[Mode] = None


class InterviewResponse(BaseModel):
    id: PyObjectId = Field(validation_alias="_id")
    user_id: PyObjectId
    title: str
    role: str
    experience_level: ExperienceLevel
    skills: List[str]
    interview_type: InterviewType
    difficulty: Difficulty
    job_description: Optional[str] = None
    mode: Mode
    status: Status
    question_count: int
    resume_id: Optional[PyObjectId] = None
    current_question_id: Optional[PyObjectId] = None
    current_question_number: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class InterviewListResponse(BaseModel):
    items: List[InterviewResponse]
    page: int
    limit: int
    total: int


# --- INTERVIEW ENGINE SCHEMAS ---

class EngineQuestionDetail(BaseModel):
    """A simplified question detail for the engine endpoints."""
    id: str
    question_number: int
    question: str
    category: str
    difficulty: Difficulty
    question_type: str = "primary"


class StartInterviewResponse(BaseModel):
    interview_id: str
    status: str
    current_question: EngineQuestionDetail


class CurrentQuestionResponse(BaseModel):
    interview_id: str
    question: EngineQuestionDetail


class SubmitAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1)
    duration_seconds: Optional[int] = None


class SubmitAnswerResponse(BaseModel):
    id: str
    interview_id: str
    question_id: str
    answer: str
    answered_at: datetime
    duration_seconds: Optional[int] = None


class NextQuestionResponse(BaseModel):
    interview_id: str
    status: str
    question: Optional[EngineQuestionDetail] = None
    message: Optional[str] = None
