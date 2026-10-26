"""
app/config/database.py

MongoDB connection using PyMongo.
Provides a reusable database reference and a connection test function.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.config.settings import settings


import certifi
import dns.resolver

# Ensure dnspython uses reliable public DNS nameservers for SRV records on Windows/private networks
try:
    dns.resolver.default_resolver = dns.resolver.Resolver()
    dns.resolver.default_resolver.nameservers = ["8.8.8.8", "1.1.1.1"]
except Exception:
    pass

try:
    client: MongoClient = MongoClient(
        settings.MONGODB_URI,
        serverSelectionTimeoutMS=5000,
        tlsCAFile=certifi.where(),
        tlsAllowInvalidCertificates=True,
    )
    db = client[settings.DATABASE_NAME]
except Exception as e:
    client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=1000)
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
