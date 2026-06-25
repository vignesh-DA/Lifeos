"""
LIFEOS Routes — Crisis Mode Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

class CrisisDraftEmailRequest(BaseModel):
    user_id: str
    task_title: str
    recipient: str
    context: str = ""


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


@router.post("/crisis/draft-email")
async def draft_email(request: CrisisDraftEmailRequest):
    """
    Draft an email using AI and push it to the user's Gmail drafts.
    """
    try:
        from langchain_groq import ChatGroq
        from config import settings
        from utils.google_api import create_gmail_draft

        groq_llm = ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model_name=settings.GROQ_MODEL,
            temperature=0.7,
            max_tokens=500,
        )
        prompt = f"""You are LIFEOS Crisis Assistant. 
The user is working on this urgent task: {request.task_title}
They need to send an email to: {request.recipient}
Additional Context: {request.context}

Write a concise, professional email draft. 
Return ONLY the email body. Do not include the subject line in the body. Do not include placeholders if possible, be creative.
"""
        response = groq_llm.invoke(prompt)
        body = response.content if hasattr(response, 'content') else str(response)
        
        subject = f"Update regarding: {request.task_title}"

        # Attempt to create draft
        draft = await create_gmail_draft(request.user_id, request.recipient, subject, body)
        
        if draft:
            return {
                "message": "Draft created in Gmail! ✉️",
                "draft_id": draft.get("id"),
                "draft_url": "https://mail.google.com/mail/u/0/#drafts"
            }
        else:
            # Fallback if Gmail is not connected or token expired
            return {
                "message": "AI Draft generated. Gmail not connected. Please connect Gmail in Settings.",
                "subject": subject,
                "body": body
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class PushDraftRequest(BaseModel):
    user_id: str
    recipient: str
    subject: str
    body: str

@router.post("/crisis/push-draft")
async def push_draft(request: PushDraftRequest):
    """
    Push a pre-generated email draft directly to Gmail.
    """
    try:
        from utils.google_api import create_gmail_draft
        draft = await create_gmail_draft(request.user_id, request.recipient, request.subject, request.body)
        
        if draft:
            return {
                "success": True,
                "message": "Draft created in Gmail! ✉️",
                "draft_id": draft.get("id"),
                "draft_url": "https://mail.google.com/mail/u/0/#drafts"
            }
        else:
            return {"success": False, "message": "Failed to create draft in Gmail."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
