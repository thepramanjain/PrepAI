"""
app/models/feedback.py

MongoDB Feedback collection setup and helpers.
One feedback document per interview (enforced by unique index on interview_id).
"""

from pymongo import ASCENDING, IndexModel

from app.config.database import db

# The collection reference
feedback_collection = db["feedback"]

# Indexes
# Unique index on interview_id — ensures one evaluation per interview (upsert replaces it)
# Index on user_id for ownership queries
indexes = [
    IndexModel([("interview_id", ASCENDING)], unique=True, background=True),
    IndexModel([("user_id", ASCENDING)], background=True),
]
feedback_collection.create_indexes(indexes)
