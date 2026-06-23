"""
LIFEOS Database — Async MongoDB Connection (Motor)
Falls back to in-memory store if MongoDB is unavailable.
"""
import ssl
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

# Global database references
client: AsyncIOMotorClient = None
db = None
_using_memory = False


async def connect_db():
    """Connect to MongoDB Atlas and initialize collections."""
    global client, db, _using_memory

    print(f"🔌 Connecting to MongoDB...")

    try:
        # Try with certifi SSL certificates (fixes Atlas SSL on Windows)
        import certifi
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
        )
        print("  ℹ️  Using certifi SSL certificates")
    except ImportError:
        # certifi not installed, try without
        print("  ⚠️  certifi not installed, trying default SSL...")
        client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=10000,
            connectTimeoutMS=10000,
        )

    db = client[settings.DATABASE_NAME]

    # Test the connection by listing collections (forces actual handshake)
    collections = await db.list_collection_names()

    if "users" not in collections:
        await db.create_collection("users")
    if "tasks" not in collections:
        await db.create_collection("tasks")
    if "patterns" not in collections:
        await db.create_collection("patterns")
    if "sessions" not in collections:
        await db.create_collection("sessions")
    if "reviews" not in collections:
        await db.create_collection("reviews")

    # Create indexes for performance
    await db.tasks.create_index([("user_id", 1), ("status", 1)])
    await db.tasks.create_index([("user_id", 1), ("priority_score", -1)])
    await db.tasks.create_index([("deadline", 1)])
    await db.patterns.create_index([("user_id", 1), ("week", 1)])
    await db.sessions.create_index([("user_id", 1)])
    await db.reviews.create_index([("user_id", 1), ("week", 1)])

    _using_memory = False
    print(f"✅ Connected to MongoDB — Database: {settings.DATABASE_NAME}")
    return db


async def use_memory_fallback():
    """Switch to in-memory store when MongoDB is unavailable."""
    global db, _using_memory
    from db.memory_store import MemoryDB, seed_sample_data

    print("  🔄 Switching to in-memory fallback store...")
    db = MemoryDB()
    _using_memory = True

    # Seed with sample data for testing
    await seed_sample_data(db)
    print("  ✅ In-memory store ready (data will be lost on restart)")
    return db


async def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("🔌 MongoDB connection closed")


def is_using_memory():
    """Check if running with in-memory fallback."""
    return _using_memory


def get_db():
    """Get database reference."""
    return db


def get_collection(name: str):
    """Get a specific collection by name."""
    if db is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return db[name]


# Collection accessors
def users_collection():
    return get_collection("users")


def tasks_collection():
    return get_collection("tasks")


def patterns_collection():
    return get_collection("patterns")


def sessions_collection():
    return get_collection("sessions")


def reviews_collection():
    return get_collection("reviews")

