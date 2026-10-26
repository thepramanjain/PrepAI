"""
app/models/user.py

MongoDB User collection setup and helpers.
"""

from pymongo import ASCENDING, IndexModel

from app.config.database import db

# The collection reference
users_collection = db["users"]

# Create a unique index on the email field to prevent duplicates.
# This runs when the module is imported; PyMongo ignores it if it already exists.
email_index = IndexModel([("email", ASCENDING)], unique=True, background=True)
try:
    users_collection.create_indexes([email_index])
except Exception:
    pass
