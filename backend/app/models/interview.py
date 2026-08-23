"""
app/models/interview.py

MongoDB Interview collection setup and helpers.
"""

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.config.database import db

# The collection reference
interviews_collection = db["interviews"]

# Indexes
# user_id — find a user's interviews
# created_at — sorting
# status — filter by draft/in_progress/completed (used by analytics)
indexes = [
    IndexModel([("user_id", ASCENDING)], background=True),
    IndexModel([("created_at", DESCENDING)], background=True),
    IndexModel([("status", ASCENDING)], background=True),
]
interviews_collection.create_indexes(indexes)
