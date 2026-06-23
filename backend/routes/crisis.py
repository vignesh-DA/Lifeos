"""
LIFEOS Routes — Crisis Mode Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CrisisActivateRequest(BaseModel):
    task_id: Optional[str] = None
    task_title: str = ""
    task_description: str = ""
    minutes_available: int = 60


class CrisisAssistRequest(BaseModel):
    task_id: str = ""
    task_title: str = ""
    step: int = 1
    step_title: str = ""
    question: str = ""


@router.post("/crisis/activate")
async def activate_crisis(request: CrisisActivateRequest):
    """
    Activate Crisis Mode — Generate an emergency battle plan
    with step-by-step micro-actions and survival probability.
    """
    task_info = {
        "title": request.task_title,
        "description": request.task_description,
    }

    # Try to get task from DB if task_id provided
    if request.task_id:
        try:
            from bson import ObjectId
            from db.mongodb import tasks_collection
            task = await tasks_collection().find_one({"_id": ObjectId(request.task_id)})
            if task:
                task_info = {
                    "title": task.get("title", request.task_title),
                    "description": task.get("description", ""),
                    "category": task.get("category", ""),
                    "estimated_hours": task.get("estimated_hours", 2),
                }
        except Exception:
            pass

    try:
        from agent.tools import crisis_activator_func
        crisis_plan = crisis_activator_func(task_info, request.minutes_available)
        return crisis_plan
    except Exception as e:
        # Fallback crisis plan if LLM fails
        return _generate_fallback_crisis_plan(task_info, request.minutes_available)


@router.post("/crisis/assist")
async def crisis_assist(request: CrisisAssistRequest):
    """
    Get AI assistance for a specific step during Crisis Mode.
    Real-time help with Gemini/Groq while the clock is ticking.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        from langchain_groq import ChatGroq
        from config import settings

        groq_llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.7,
            max_tokens=500,
        )
        prompt = f"""You are LIFEOS Crisis Assistant. The user is in CRISIS MODE working on:
Task: {request.task_title}
Current Step: Step {request.step} — {request.step_title}

The user needs help RIGHT NOW. Be concise, actionable, and fast.
No lengthy explanations. Give them exactly what they need to move forward.

User's question: {request.question}

Respond with clear, actionable help in 3-5 sentences max:"""

        response = groq_llm.invoke(prompt)
        answer = response.content if hasattr(response, 'content') else str(response)

        return {
            "step": request.step,
            "question": request.question,
            "assistance": answer,
            "message": "AI assistance delivered ⚡",
        }
    except Exception as e:
        return {
            "step": request.step,
            "question": request.question,
            "assistance": f"Quick tip for Step {request.step} — {request.step_title}: Focus on the most essential part only. Write/do just enough to show you understand the core concept. Perfection is the enemy of done.",
            "message": "Fallback assistance provided",
        }


def _generate_fallback_crisis_plan(task_info: dict, minutes: int) -> dict:
    """Generate a simple crisis plan without LLM (fallback)."""
    title = task_info.get("title", "Your Task")
    total_steps = 5
    time_per_step = minutes // total_steps

    steps = [
        {
            "step": 1,
            "title": "Understand the requirements",
            "duration": max(time_per_step // 3, 5),
            "ai_help": "Paste the requirements and I'll extract the key points you need to cover.",
        },
        {
            "step": 2,
            "title": "Create a quick outline",
            "duration": max(time_per_step // 2, 5),
            "ai_help": "Tell me the topic and I'll generate a structure for you instantly.",
        },
        {
            "step": 3,
            "title": "Complete the main content",
            "duration": int(minutes * 0.45),
            "ai_help": "Send me any section you're stuck on — I'll help you move forward.",
        },
        {
            "step": 4,
            "title": "Review and polish",
            "duration": int(minutes * 0.15),
            "ai_help": "Paste your work — I'll check for gaps and suggest improvements.",
        },
        {
            "step": 5,
            "title": "Final check and submit",
            "duration": max(int(minutes * 0.05), 5),
            "ai_help": None,
        },
    ]

    # Calculate survival probability
    estimated_hours = task_info.get("estimated_hours", 2)
    needed_minutes = estimated_hours * 60
    survival = min(95, max(15, int((minutes / max(needed_minutes, 1)) * 100)))

    return {
        "task": title,
        "time_available": minutes,
        "survival_probability": survival,
        "steps": steps,
        "message": f"Crisis plan ready! {survival}% survival chance. Let's go! 🚨",
    }
