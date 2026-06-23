"""
LIFEOS Routes — Agent Planning Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# ─── Request Models ───

class BrainDumpRequest(BaseModel):
    text: str
    user_id: str = "default_user"


class AgentPlanRequest(BaseModel):
    user_id: str
    context: str
    mood: Optional[str] = None  # tired|energized|stressed|distracted


class MoodRequest(BaseModel):
    user_id: str
    mood: str  # tired|energized|stressed|distracted


class EmailDraftRequest(BaseModel):
    task_title: str
    task_deadline: str = ""
    reason: str
    recipient_name: str = "Professor"
    user_name: str = "Student"


# ─── Endpoints ───

@router.post("/brain-dump")
async def brain_dump(request: BrainDumpRequest):
    """
    Extract structured tasks from messy user input using NLP.
    This is the core brain dump → organized tasks pipeline.
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    try:
        from nlp.brain_dump import process_brain_dump
        result = process_brain_dump(request.text)

        # Save extracted tasks to MongoDB
        from db.mongodb import tasks_collection
        from datetime import datetime, timezone

        saved_tasks = []
        for task in result.get("tasks", []):
            task_doc = {
                "user_id": request.user_id,
                "title": task["title"],
                "description": "",
                "category": task.get("category", "personal"),
                "priority_score": task.get("urgency_score", 5.0),
                "urgency_score": task.get("urgency_score", 5.0),
                "deadline": task.get("deadline"),
                "deadline_confidence": task.get("deadline_confidence", "medium"),
                "estimated_hours": task.get("estimated_hours", 1.0),
                "actual_hours": 0,
                "status": "pending",
                "postpone_count": 0,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "completed_at": None,
                "extracted_from": "brain_dump",
                "ai_steps": [],
                "tags": task.get("extracted_keywords", []),
            }
            insert_result = await tasks_collection().insert_one(task_doc)
            task_doc["_id"] = str(insert_result.inserted_id)
            saved_tasks.append(task_doc)

        result["saved_tasks"] = saved_tasks
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Brain dump processing failed: {str(e)}")


@router.post("/agent/plan")
async def agent_plan(request: AgentPlanRequest):
    """
    Autonomous agent creates a complete life plan.
    Uses LangChain agent with all 10 tools.
    """
    try:
        from agent.life_agent import run_life_agent
        result = await run_life_agent(
            user_id=request.user_id,
            user_input=request.context,
            mood=request.mood,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent planning failed: {str(e)}")


@router.post("/mood")
async def set_mood(request: MoodRequest):
    """
    Set user's current mood and get mood-adjusted schedule.
    The agent restructures today's plan based on energy level.
    """
    valid_moods = ["tired", "energized", "stressed", "distracted"]
    if request.mood not in valid_moods:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mood. Must be one of: {valid_moods}"
        )

    try:
        # Get user's current tasks
        from db.mongodb import tasks_collection, users_collection
        from datetime import datetime, timezone

        cursor = tasks_collection().find({
            "user_id": request.user_id,
            "status": {"$in": ["pending", "in_progress"]}
        }).sort("priority_score", -1)

        tasks = []
        async for task in cursor:
            task["_id"] = str(task["_id"])
            tasks.append(task)

        # Record mood in user history
        await users_collection().update_one(
            {"user_id": request.user_id},
            {"$push": {
                "mood_history": {
                    "mood": request.mood,
                    "date": datetime.now(timezone.utc).isoformat()
                }
            }},
            upsert=True,
        )

        # Use mood-aware scheduler
        from agent.tools import mood_aware_scheduler_func
        adjusted_schedule = mood_aware_scheduler_func(request.mood, tasks)

        return {
            "mood": request.mood,
            "adjusted_schedule": adjusted_schedule,
            "task_count": len(tasks),
            "message": f"Schedule adjusted for {request.mood} mood 🎭",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mood adjustment failed: {str(e)}")


@router.post("/email/draft")
async def draft_email(request: EmailDraftRequest):
    """
    Draft a professional extension request email using LLM.
    """
    try:
        from agent.tools import email_drafter_func
        email_text = email_drafter_func(
            task_title=request.task_title,
            deadline=request.task_deadline,
            reason=request.reason,
            recipient=request.recipient_name,
            user_name=request.user_name,
        )
        return {
            "email": email_text,
            "message": "Email drafted successfully ✉️",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email drafting failed: {str(e)}")
