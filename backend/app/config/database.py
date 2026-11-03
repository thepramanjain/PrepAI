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

# Ensure dnspython includes reliable public DNS nameservers for SRV records on Windows/private networks
try:
    if dns.resolver.default_resolver is None:
        dns.resolver.default_resolver = dns.resolver.Resolver()
    existing_ns = list(dns.resolver.default_resolver.nameservers)
    for fallback_ns in ["8.8.8.8", "1.1.1.1"]:
        if fallback_ns not in existing_ns:
            existing_ns.append(fallback_ns)
    dns.resolver.default_resolver.nameservers = existing_ns
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
