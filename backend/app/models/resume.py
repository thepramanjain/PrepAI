"""
app/models/resume.py

MongoDB Resume collection setup and helpers.
"""

from pymongo import ASCENDING, DESCENDING, IndexModel

from app.config.database import db

# The collection reference
resumes_collection = db["resumes"]

# Indexes
# Index on user_id to quickly find a user's resumes
# Index on created_at for sorting newest first
indexes = [
    IndexModel([("user_id", ASCENDING)], background=True),
    IndexModel([("created_at", DESCENDING)], background=True),
]
resumes_collection.create_indexes(indexes)
