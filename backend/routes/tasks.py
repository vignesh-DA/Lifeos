"""
LIFEOS Routes — Task CRUD Endpoints
"""
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from db.mongodb import tasks_collection, users_collection

router = APIRouter()


# ─── Pydantic Models ───

class TaskCreate(BaseModel):
    user_id: str
    title: str
    description: str = ""
    category: str = "personal"  # academic|career|finance|personal|health
    deadline: Optional[str] = None
    deadline_confidence: str = "medium"  # high|medium|low
    estimated_hours: float = 1.0
    extracted_from: str = "manual"  # brain_dump|manual|voice
    tags: list[str] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    deadline: Optional[str] = None
    estimated_hours: Optional[float] = None
    status: Optional[str] = None
    tags: Optional[list[str]] = None


def task_serializer(task: dict) -> dict:
    """Convert MongoDB task document to JSON-serializable dict."""
    task["_id"] = str(task["_id"])
    if "user_id" in task and isinstance(task["user_id"], ObjectId):
        task["user_id"] = str(task["user_id"])
    return task


# ─── Endpoints ───

@router.get("/tasks/{user_id}")
async def get_tasks(user_id: str, status: Optional[str] = None):
    """Get all tasks for a user, sorted by priority_score descending."""
    query = {"user_id": user_id}
    if status:
        query["status"] = status

    cursor = tasks_collection().find(query).sort("priority_score", -1)
    tasks = []
    async for task in cursor:
        tasks.append(task_serializer(task))

    return {"tasks": tasks, "count": len(tasks)}


@router.post("/tasks")
async def create_task(task_data: TaskCreate):
    """Create a new task with AI-scored priority."""
    # Score priority using ML model
    priority_score = 5.0  # Default
    try:
        from ml.priority import predict_priority
        priority_score = predict_priority(task_data.model_dump())
    except Exception:
        pass

    task_doc = {
        "user_id": task_data.user_id,
        "title": task_data.title,
        "description": task_data.description,
        "category": task_data.category,
        "priority_score": priority_score,
        "urgency_score": priority_score,
        "deadline": task_data.deadline,
        "deadline_confidence": task_data.deadline_confidence,
        "estimated_hours": task_data.estimated_hours,
        "actual_hours": 0,
        "status": "pending",
        "postpone_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "extracted_from": task_data.extracted_from,
        "ai_steps": [],
        "tags": task_data.tags,
    }

    result = await tasks_collection().insert_one(task_doc)
    task_doc["_id"] = str(result.inserted_id)

    return {"task": task_doc, "message": "Task created successfully"}


@router.put("/tasks/{task_id}")
async def update_task(task_id: str, task_data: TaskUpdate):
    """Update a task partially."""
    update_fields = {k: v for k, v in task_data.model_dump().items() if v is not None}

    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    # If status changed to pending again, increment postpone count
    if update_fields.get("status") == "pending":
        update_fields["postpone_count"] = {"$inc": 1}

    result = await tasks_collection().update_one(
        {"_id": ObjectId(task_id)},
        {"$set": update_fields}
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    updated = await tasks_collection().find_one({"_id": ObjectId(task_id)})
    return {"task": task_serializer(updated), "message": "Task updated"}


@router.put("/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    """Mark a task as completed and update user streak."""
    task = await tasks_collection().find_one({"_id": ObjectId(task_id)})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    now = datetime.now(timezone.utc).isoformat()
    await tasks_collection().update_one(
        {"_id": ObjectId(task_id)},
        {"$set": {"status": "completed", "completed_at": now}}
    )

    # Update user streak
    user_id = task.get("user_id")
    user = await users_collection().find_one({"user_id": user_id})

    streak_days = 1
    best_streak = 1

    if user:
        streak_days = user.get("streak_days", 0) + 1
        best_streak = max(user.get("best_streak", 0), streak_days)

        await users_collection().update_one(
            {"user_id": user_id},
            {"$set": {
                "streak_days": streak_days,
                "best_streak": best_streak,
                "last_completion": now,
            }}
        )
    else:
        await users_collection().insert_one({
            "user_id": user_id,
            "name": "User",
            "streak_days": 1,
            "best_streak": 1,
            "productivity_score": 50.0,
            "peak_hours": [9, 10, 11],
            "procrastination_triggers": [],
            "mood_history": [],
            "badges": [],
            "created_at": now,
            "last_completion": now,
        })

    # Check for new badges
    badges_earned = []
    if streak_days >= 3:
        badges_earned.append("🔥 3-Day Streak!")
    if streak_days >= 7:
        badges_earned.append("⚡ Week Warrior!")
    if streak_days >= 14:
        badges_earned.append("🏆 Unstoppable!")

    # Count completions by category for category badges
    completed_count = await tasks_collection().count_documents({
        "user_id": user_id, "status": "completed", "category": task.get("category")
    })
    if completed_count >= 10:
        category = task.get("category", "").title()
        badges_earned.append(f"🎯 {category} Master!")

    return {
        "message": "Task completed! 🎉",
        "streak_days": streak_days,
        "best_streak": best_streak,
        "badges_earned": badges_earned,
    }


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    result = await tasks_collection().delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    return {"message": "Task deleted", "task_id": task_id}


@router.put("/tasks/{task_id}/postpone")
async def postpone_task(task_id: str):
    """Postpone a task — increments postpone counter."""
    result = await tasks_collection().update_one(
        {"_id": ObjectId(task_id)},
        {
            "$inc": {"postpone_count": 1},
            "$set": {"status": "pending"}
        }
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")

    updated = await tasks_collection().find_one({"_id": ObjectId(task_id)})
    return {
        "task": task_serializer(updated),
        "message": f"Task postponed ({updated.get('postpone_count', 0)} times total)",
    }


@router.get("/user/{user_id}/streak")
async def get_streak(user_id: str):
    """Get user's current streak, best streak, and badges."""
    user = await users_collection().find_one({"user_id": user_id})

    if not user:
        return {
            "streak_days": 0,
            "best_streak": 0,
            "badges": [],
            "productivity_score": 0,
        }

    return {
        "streak_days": user.get("streak_days", 0),
        "best_streak": user.get("best_streak", 0),
        "badges": user.get("badges", []),
        "productivity_score": user.get("productivity_score", 0),
    }
