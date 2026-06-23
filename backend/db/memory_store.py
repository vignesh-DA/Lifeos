"""
LIFEOS — In-Memory Fallback Store
Mimics Motor's async MongoDB collection API so the app works without a database.
Auto-seeds with sample tasks for testing.
"""
from datetime import datetime, timezone, timedelta
from bson import ObjectId


class MemoryCursor:
    """Mimics Motor's async cursor."""

    def __init__(self, docs):
        self._docs = list(docs)
        self._index = 0

    def sort(self, key, direction=-1):
        try:
            self._docs.sort(key=lambda d: d.get(key, 0), reverse=(direction == -1))
        except TypeError:
            pass
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._index].copy()
        self._index += 1
        return doc

    async def to_list(self, length=None):
        if length:
            return [d.copy() for d in self._docs[:length]]
        return [d.copy() for d in self._docs]


class InsertOneResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, modified_count):
        self.modified_count = modified_count


class DeleteResult:
    def __init__(self, deleted_count):
        self.deleted_count = deleted_count


class MemoryCollection:
    """Mimics Motor's AsyncIOMotorCollection with in-memory storage."""

    def __init__(self, name):
        self.name = name
        self._docs = {}  # ObjectId -> doc

    def find(self, query=None, *args, **kwargs):
        docs = self._match(query or {})
        return MemoryCursor(docs)

    async def find_one(self, query=None):
        docs = self._match(query or {})
        return docs[0].copy() if docs else None

    async def insert_one(self, doc):
        doc = doc.copy()
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self._docs[doc["_id"]] = doc
        return InsertOneResult(doc["_id"])

    async def update_one(self, query, update, upsert=False):
        docs = self._match(query)
        if not docs:
            if upsert:
                new_doc = {}
                # Extract query fields
                for k, v in query.items():
                    if not k.startswith("$"):
                        new_doc[k] = v
                # Apply $set
                if "$set" in update:
                    new_doc.update(update["$set"])
                if "$push" in update:
                    for k, v in update["$push"].items():
                        new_doc.setdefault(k, []).append(v)
                await self.insert_one(new_doc)
                return UpdateResult(1)
            return UpdateResult(0)

        doc = docs[0]
        oid = doc["_id"]

        if "$set" in update:
            self._docs[oid].update(update["$set"])
        if "$inc" in update:
            for k, v in update["$inc"].items():
                self._docs[oid][k] = self._docs[oid].get(k, 0) + v
        if "$push" in update:
            for k, v in update["$push"].items():
                self._docs[oid].setdefault(k, []).append(v)

        # Simple direct update (no operators)
        if not any(k.startswith("$") for k in update):
            self._docs[oid].update(update)

        return UpdateResult(1)

    async def delete_one(self, query):
        docs = self._match(query)
        if docs:
            del self._docs[docs[0]["_id"]]
            return DeleteResult(1)
        return DeleteResult(0)

    async def count_documents(self, query=None):
        return len(self._match(query or {}))

    async def create_index(self, keys):
        pass  # No-op for in-memory

    def _match(self, query):
        """Simple query matcher supporting basic MongoDB query operators."""
        results = []
        for doc in self._docs.values():
            if self._doc_matches(doc, query):
                results.append(doc)
        return results

    def _doc_matches(self, doc, query):
        for key, value in query.items():
            if key.startswith("$"):
                continue
            doc_val = doc.get(key)
            if isinstance(value, ObjectId):
                if doc_val != value:
                    return False
            elif isinstance(value, dict):
                # Handle operators like $in, $gte, etc.
                for op, op_val in value.items():
                    if op == "$in":
                        if doc_val not in op_val:
                            return False
                    elif op == "$gte":
                        if doc_val is None or doc_val < op_val:
                            return False
                    elif op == "$lte":
                        if doc_val is None or doc_val > op_val:
                            return False
                    elif op == "$ne":
                        if doc_val == op_val:
                            return False
            else:
                if doc_val != value:
                    return False
        return True


class MemoryDB:
    """Mimics a MongoDB database with named collections."""

    def __init__(self):
        self._collections = {}

    def __getitem__(self, name):
        if name not in self._collections:
            self._collections[name] = MemoryCollection(name)
        return self._collections[name]

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    async def list_collection_names(self):
        return list(self._collections.keys())

    async def create_collection(self, name):
        if name not in self._collections:
            self._collections[name] = MemoryCollection(name)


def _make_deadline(days_from_now, hour=23, minute=59):
    """Create an ISO deadline string N days from now."""
    d = datetime.now(timezone.utc) + timedelta(days=days_from_now)
    d = d.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return d.isoformat()


SAMPLE_TASKS = [
    {
        "user_id": "lifeos_user_1",
        "title": "Complete Machine Learning Assignment — Neural Networks",
        "description": "Implement a feedforward neural network from scratch using NumPy. Include backpropagation, gradient descent, and train on MNIST dataset.",
        "category": "academic",
        "priority_score": 9.2,
        "urgency_score": 9.2,
        "deadline": _make_deadline(1),
        "deadline_confidence": "high",
        "estimated_hours": 5.0,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 2,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "completed_at": None,
        "extracted_from": "brain_dump",
        "ai_steps": [],
        "tags": ["ML", "neural-network", "assignment"],
    },
    {
        "user_id": "lifeos_user_1",
        "title": "Pay electricity bill before late fee",
        "description": "₹2,400 due. Pay via PhonePe or bank app.",
        "category": "finance",
        "priority_score": 8.5,
        "urgency_score": 8.5,
        "deadline": _make_deadline(0, 18, 0),
        "deadline_confidence": "high",
        "estimated_hours": 0.25,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 1,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
        "completed_at": None,
        "extracted_from": "brain_dump",
        "ai_steps": [],
        "tags": ["bill", "finance", "urgent"],
    },
    {
        "user_id": "lifeos_user_1",
        "title": "Prepare slides for Software Engineering presentation",
        "description": "Topic: Agile vs Waterfall methodology. 15-minute presentation with case studies.",
        "category": "academic",
        "priority_score": 7.8,
        "urgency_score": 7.8,
        "deadline": _make_deadline(2),
        "deadline_confidence": "high",
        "estimated_hours": 3.0,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 0,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "completed_at": None,
        "extracted_from": "brain_dump",
        "ai_steps": [],
        "tags": ["presentation", "SE", "slides"],
    },
    {
        "user_id": "lifeos_user_1",
        "title": "Fix portfolio website — contact form broken",
        "description": "Form submissions return 500 error. Check Netlify serverless function and email service integration.",
        "category": "career",
        "priority_score": 6.5,
        "urgency_score": 6.5,
        "deadline": _make_deadline(3),
        "deadline_confidence": "medium",
        "estimated_hours": 2.0,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 0,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        "completed_at": None,
        "extracted_from": "manual",
        "ai_steps": [],
        "tags": ["portfolio", "bug-fix", "web"],
    },
    {
        "user_id": "lifeos_user_1",
        "title": "Go for a 30-min run + stretching",
        "description": "Morning run in the park. Don't skip the cool-down stretches this time.",
        "category": "health",
        "priority_score": 5.0,
        "urgency_score": 5.0,
        "deadline": _make_deadline(0, 7, 0),
        "deadline_confidence": "low",
        "estimated_hours": 0.75,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 3,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
        "completed_at": None,
        "extracted_from": "manual",
        "ai_steps": [],
        "tags": ["exercise", "health", "morning"],
    },
    {
        "user_id": "lifeos_user_1",
        "title": "Submit internship application — Google SWE",
        "description": "Finalize resume, write cover letter, and submit through careers portal.",
        "category": "career",
        "priority_score": 8.9,
        "urgency_score": 8.9,
        "deadline": _make_deadline(4),
        "deadline_confidence": "high",
        "estimated_hours": 2.5,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 0,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "completed_at": None,
        "extracted_from": "brain_dump",
        "ai_steps": [],
        "tags": ["internship", "google", "resume"],
    },
    {
        "user_id": "lifeos_user_1",
        "title": "Read Chapter 5 — Database Systems textbook",
        "description": "SQL joins, normalization (1NF, 2NF, 3NF, BCNF). Make notes for exam.",
        "category": "academic",
        "priority_score": 6.0,
        "urgency_score": 6.0,
        "deadline": _make_deadline(5),
        "deadline_confidence": "medium",
        "estimated_hours": 2.0,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 1,
        "created_at": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
        "completed_at": None,
        "extracted_from": "brain_dump",
        "ai_steps": [],
        "tags": ["DBMS", "reading", "exam-prep"],
    },
    {
        "user_id": "lifeos_user_1",
        "title": "Call Mom — she asked about weekend plans",
        "description": "",
        "category": "personal",
        "priority_score": 4.0,
        "urgency_score": 4.0,
        "deadline": _make_deadline(1, 20, 0),
        "deadline_confidence": "low",
        "estimated_hours": 0.5,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 0,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),
        "completed_at": None,
        "extracted_from": "manual",
        "ai_steps": [],
        "tags": ["family", "call"],
    },
    {
        "user_id": "lifeos_user_1",
        "title": "Grocery run — milk, eggs, bread, bananas",
        "description": "Also check if there's a discount on protein powder.",
        "category": "personal",
        "priority_score": 3.5,
        "urgency_score": 3.5,
        "deadline": _make_deadline(1),
        "deadline_confidence": "low",
        "estimated_hours": 1.0,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 0,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        "completed_at": None,
        "extracted_from": "brain_dump",
        "ai_steps": [],
        "tags": ["groceries", "shopping"],
    },
    {
        "user_id": "lifeos_user_1",
        "title": "LeetCode daily challenge — 3 medium problems",
        "description": "Focus on dynamic programming and graph problems.",
        "category": "career",
        "priority_score": 5.5,
        "urgency_score": 5.5,
        "deadline": _make_deadline(0, 23, 59),
        "deadline_confidence": "medium",
        "estimated_hours": 2.0,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 0,
        "created_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
        "completed_at": None,
        "extracted_from": "manual",
        "ai_steps": [],
        "tags": ["leetcode", "DSA", "practice"],
    },
]


async def seed_sample_data(db: MemoryDB):
    """Seed the in-memory DB with sample tasks and a user profile."""
    print("  📦 Seeding in-memory store with sample data...")

    # Seed tasks
    tasks_col = db["tasks"]
    for task in SAMPLE_TASKS:
        task_copy = task.copy()
        task_copy["_id"] = ObjectId()
        tasks_col._docs[task_copy["_id"]] = task_copy

    # Seed user profile
    users_col = db["users"]
    user_doc = {
        "_id": ObjectId(),
        "user_id": "lifeos_user_1",
        "name": "Vignesh",
        "streak_days": 4,
        "best_streak": 12,
        "productivity_score": 72.0,
        "peak_hours": [9, 10, 11, 14, 15],
        "procrastination_triggers": ["social_media", "youtube"],
        "mood_history": [
            {"mood": "energized", "date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()},
            {"mood": "stressed", "date": (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()},
        ],
        "badges": ["🔥 3-Day Streak!", "🎯 Academic Master!"],
        "created_at": (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),
        "last_completion": (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat(),
    }
    users_col._docs[user_doc["_id"]] = user_doc

    print(f"  ✅ Seeded {len(SAMPLE_TASKS)} tasks + 1 user profile")
