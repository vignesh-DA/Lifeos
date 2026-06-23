"""
LIFEOS Database — Async MongoDB Connection (Motor)
"""
from motor.motor_asyncio import AsyncIOMotorClient
from config import settings

# Global database references
client: AsyncIOMotorClient = None
db = None


async def connect_db():
    """Connect to MongoDB Atlas and initialize collections."""
    global client, db
    print(f"🔌 Connecting to MongoDB...")
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]

    # Ensure collections exist with indexes
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

    print(f"✅ Connected to MongoDB — Database: {settings.DATABASE_NAME}")
    return db


async def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()
        print("🔌 MongoDB connection closed")


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
