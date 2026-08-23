"""
app/schemas/ai_question.py

Pydantic schemas for Gemini AI question generation.
"""

from typing import List
from pydantic import BaseModel, Field

from app.schemas.interview import Difficulty


class GeneratedQuestion(BaseModel):
    question: str = Field(..., description="The interview question text.")
    category: str = Field(..., description="The category or topic of the question (e.g., React, Python).")
    difficulty: Difficulty = Field(..., description="The difficulty level of the question.")


class GeneratedQuestionList(BaseModel):
    questions: List[GeneratedQuestion] = Field(..., description="A list of generated interview questions.")
