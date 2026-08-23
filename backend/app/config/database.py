"""
app/config/database.py

MongoDB connection using PyMongo.
Provides a reusable database reference and a connection test function.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.config.settings import settings


import certifi

# Create the MongoDB client with a reasonable timeout (5 seconds)
# so the app doesn't hang forever if MongoDB is unreachable.
client: MongoClient = MongoClient(
    settings.MONGODB_URI,
    serverSelectionTimeoutMS=5000,
    tlsCAFile=certifi.where(),
    tlsAllowInvalidCertificates=True,
)

# Select the database — no collections are created yet
db = client[settings.DATABASE_NAME]


def test_connection() -> bool:
    """
    Ping MongoDB to verify the connection is alive.
    Returns True if connected, raises an exception otherwise.
    """
    try:
        client.admin.command("ping")
        return True
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        raise ConnectionError(f"MongoDB connection failed: {e}")
