"""
app/models/question.py

MongoDB Question collection setup and helpers.
"""

from pymongo import ASCENDING, IndexModel

from app.config.database import db

# The collection reference
questions_collection = db["questions"]

# Indexes
# Index on interview_id to quickly find questions for an interview
# Index on question_number to sort questions
# Index on parent_question_id for follow-up lookups
indexes = [
    IndexModel([("interview_id", ASCENDING), ("question_number", ASCENDING)], background=True),
    IndexModel([("parent_question_id", ASCENDING)], background=True, sparse=True),
]
try:
    questions_collection.create_indexes(indexes)
except Exception:
    pass
