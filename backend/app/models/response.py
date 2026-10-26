"""
app/models/response.py

MongoDB Response collection setup and helpers.
"""

from pymongo import ASCENDING, IndexModel

from app.config.database import db

# The collection reference
responses_collection = db["responses"]

# Indexes
# Index on interview_id and question_id for quick lookups
# Unique compound index to prevent duplicate responses per user/question
indexes = [
    IndexModel([("interview_id", ASCENDING)], background=True),
    IndexModel([("question_id", ASCENDING)], background=True),
    IndexModel([("user_id", ASCENDING)], background=True),
    IndexModel(
        [("interview_id", ASCENDING), ("question_id", ASCENDING), ("user_id", ASCENDING)],
        unique=True,
        background=True,
    ),
]
try:
    responses_collection.create_indexes(indexes)
except Exception:
    pass
