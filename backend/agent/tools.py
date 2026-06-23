"""
LIFEOS Agent — All 10 Agent Tools
These are the hands and legs of the autonomous agent.
"""
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from config import settings


# ─── LLM Initialization ───

_llm = None
_fallback_llm = None


def get_llm():
    """Get primary LLM (Groq for speed) with Gemini fallback."""
    global _llm, _fallback_llm

    if _llm is None:
        # Try Groq first (faster, higher rate limits)
        if settings.GROQ_API_KEY:
            try:
                from langchain_groq import ChatGroq
                _llm = ChatGroq(
                    api_key=settings.GROQ_API_KEY,
                    model_name=settings.GROQ_MODEL,
                    temperature=settings.LLM_TEMPERATURE,
                    max_tokens=settings.LLM_MAX_TOKENS,
                )
                print("  🧠 Using Groq LLM (primary)")
            except Exception as e:
                print(f"  ⚠️ Groq init failed: {e}")

        # Gemini as fallback
        if settings.GEMINI_API_KEY:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                _fallback_llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash",
                    google_api_key=settings.GEMINI_API_KEY,
                    temperature=settings.LLM_TEMPERATURE,
                    max_output_tokens=settings.LLM_MAX_TOKENS,
                )
                if _llm is None:
                    _llm = _fallback_llm
                    print("  🧠 Using Gemini LLM (primary — Groq unavailable)")
                else:
                    print("  🧠 Gemini LLM ready (fallback)")
            except Exception as e:
                print(f"  ⚠️ Gemini init failed: {e}")

    if _llm is None:
        raise RuntimeError("No LLM configured. Set GROQ_API_KEY or GEMINI_API_KEY in .env")

    return _llm


def invoke_llm(prompt: str) -> str:
    """Invoke LLM with automatic fallback."""
    global _llm, _fallback_llm
    try:
        response = get_llm().invoke(prompt)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        if _fallback_llm and _fallback_llm != _llm:
            try:
                response = _fallback_llm.invoke(prompt)
                return response.content if hasattr(response, 'content') else str(response)
            except Exception:
                pass
        return f"LLM unavailable: {str(e)}"


# ═══════════════════════════════════════════════
# TOOL 1 — Brain Dump NLP
# ═══════════════════════════════════════════════

def brain_dump_nlp_func(text: str) -> dict:
    """Extract structured tasks from messy user input using spaCy NLP."""
    from nlp.brain_dump import process_brain_dump
    return process_brain_dump(text)


# ═══════════════════════════════════════════════
# TOOL 2 — Priority Scorer
# ═══════════════════════════════════════════════

def priority_scorer_func(tasks: list) -> list:
    """ML model scores each task 0-10 urgency. Returns sorted by priority."""
    from ml.priority import predict_priorities
    return predict_priorities(tasks)


# ═══════════════════════════════════════════════
# TOOL 3 — Schedule Builder
# ═══════════════════════════════════════════════

def schedule_builder_func(tasks: list, available_hours: Optional[dict] = None) -> dict:
    """
    Build an optimal daily schedule from prioritized tasks.
    Assigns tasks to specific time slots with breaks.
    """
    if not available_hours:
        available_hours = {
            "start": 9,
            "end": 21,
            "peak_start": 9,
            "peak_end": 12,
        }

    start_hour = available_hours.get("start", 9)
    end_hour = available_hours.get("end", 21)
    peak_start = available_hours.get("peak_start", 9)
    peak_end = available_hours.get("peak_end", 12)

    schedule = []
    current_hour = start_hour
    current_minutes = 0

    # Sort: highest priority first, but put quick tasks (<30min) at boundaries
    sorted_tasks = sorted(tasks, key=lambda t: t.get("priority_score", 5), reverse=True)

    # Separate peak and non-peak tasks
    hard_tasks = [t for t in sorted_tasks if t.get("estimated_hours", 1) >= 1.5]
    easy_tasks = [t for t in sorted_tasks if t.get("estimated_hours", 1) < 1.5]

    # Schedule hard tasks during peak hours first
    tasks_to_schedule = []
    for t in hard_tasks:
        tasks_to_schedule.append(t)
    for t in easy_tasks:
        tasks_to_schedule.append(t)

    for task in tasks_to_schedule:
        if current_hour >= end_hour:
            break

        est_hours = task.get("estimated_hours", 1.0)
        est_minutes = int(est_hours * 60)

        # Format time
        time_str = f"{current_hour:02d}:{current_minutes:02d}"

        # Determine why this task is scheduled here
        reasons = []
        if peak_start <= current_hour < peak_end:
            reasons.append("Peak productivity hours")
        if task.get("priority_score", 0) >= 8:
            reasons.append(f"High priority ({task.get('priority_score', 0)}/10)")
        if task.get("deadline"):
            reasons.append(f"Deadline: {task.get('deadline')}")
        if task.get("postpone_count", 0) > 0:
            reasons.append(f"Postponed {task.get('postpone_count')} times")

        schedule.append({
            "time": time_str,
            "task": task.get("title", "Untitled"),
            "duration_minutes": est_minutes,
            "category": task.get("category", "personal"),
            "priority_score": task.get("priority_score", 5.0),
            "reasoning": reasons,
            "type": "task",
        })

        # Advance time
        total_minutes = current_hour * 60 + current_minutes + est_minutes
        current_hour = total_minutes // 60
        current_minutes = total_minutes % 60

        # Add break after every 90+ minutes of work
        if est_minutes >= 90 or (schedule and len(schedule) % 3 == 0):
            schedule.append({
                "time": f"{current_hour:02d}:{current_minutes:02d}",
                "task": "Break ☕",
                "duration_minutes": 15,
                "category": "break",
                "type": "break",
            })
            total_minutes += 15
            current_hour = total_minutes // 60
            current_minutes = total_minutes % 60

    return {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "schedule": schedule,
        "total_tasks": len([s for s in schedule if s.get("type") == "task"]),
        "total_hours": round(sum(
            s.get("duration_minutes", 0) for s in schedule if s.get("type") == "task"
        ) / 60, 1),
        "free_hours": round(max(0, (end_hour - start_hour) - sum(
            s.get("duration_minutes", 0) for s in schedule
        ) / 60), 1),
    }


# ═══════════════════════════════════════════════
# TOOL 4 — Conflict Detector
# ═══════════════════════════════════════════════

def conflict_detector_func(schedule: dict) -> list:
    """Find overlapping commitments and impossible time constraints."""
    conflicts = []
    items = schedule.get("schedule", [])

    for i, item in enumerate(items):
        if item.get("type") == "break":
            continue

        duration = item.get("duration_minutes", 60)
        priority = item.get("priority_score", 5)

        # Check for unrealistic time estimates
        if duration > 240:  # More than 4 hours straight
            conflicts.append({
                "type": "unrealistic_duration",
                "task": item.get("task"),
                "message": f"'{item.get('task')}' is scheduled for {duration} minutes straight. "
                           f"Consider breaking it into smaller sessions.",
                "severity": "warning",
                "suggestion": "Break into 2-hour blocks with 15-min breaks between.",
            })

        # Check for back-to-back hard tasks
        if i > 0 and items[i-1].get("type") == "task":
            prev_duration = items[i-1].get("duration_minutes", 0)
            if prev_duration >= 90 and duration >= 90:
                conflicts.append({
                    "type": "energy_conflict",
                    "tasks": [items[i-1].get("task"), item.get("task")],
                    "message": f"Two heavy tasks back-to-back. Productivity will crash.",
                    "severity": "warning",
                    "suggestion": "Add a 15-min break between these tasks.",
                })

    # Check total workload
    total_task_minutes = sum(
        item.get("duration_minutes", 0)
        for item in items if item.get("type") == "task"
    )
    if total_task_minutes > 600:  # More than 10 hours
        conflicts.append({
            "type": "overload",
            "message": f"Total workload is {total_task_minutes // 60} hours. "
                       f"This is unsustainable.",
            "severity": "critical",
            "suggestion": "Move lower-priority tasks to tomorrow.",
        })

    return conflicts


# ═══════════════════════════════════════════════
# TOOL 5 — Crisis Activator
# ═══════════════════════════════════════════════

def crisis_activator_func(task: dict, minutes_available: int) -> dict:
    """Generate emergency battle plan with step-by-step survival strategy."""
    task_title = task.get("title", "Your Task")
    task_desc = task.get("description", "")
    task_category = task.get("category", "general")

    prompt = f"""You are LIFEOS Crisis Planner. Generate a survival battle plan.

TASK: {task_title}
DESCRIPTION: {task_desc}
CATEGORY: {task_category}
TIME AVAILABLE: {minutes_available} minutes

Create exactly 5-6 steps that fit within {minutes_available} minutes total.
Each step must have: title, duration in minutes, and a specific AI help offer.

Respond in valid JSON format:
{{
    "steps": [
        {{"step": 1, "title": "step title", "duration": minutes, "ai_help": "specific help offered"}},
        ...
    ],
    "survival_probability": <number 1-100>,
    "key_strategy": "one sentence strategy"
}}

Be realistic about the time. If {minutes_available} minutes isn't enough, say so in key_strategy.
Make steps actionable and specific, not vague."""

    try:
        response = invoke_llm(prompt)
        # Try to parse JSON from response
        json_match = response
        if "```json" in response:
            json_match = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            json_match = response.split("```")[1].split("```")[0]

        plan = json.loads(json_match.strip())

        return {
            "task": task_title,
            "time_available": minutes_available,
            "survival_probability": plan.get("survival_probability", 65),
            "steps": plan.get("steps", []),
            "key_strategy": plan.get("key_strategy", "Focus on what matters most."),
            "message": f"Crisis plan ready! Let's survive this. 🚨",
        }
    except Exception:
        # Fallback to template-based plan
        return _template_crisis_plan(task_title, minutes_available)


def _template_crisis_plan(title: str, minutes: int) -> dict:
    """Template-based crisis plan when LLM is unavailable."""
    step_time = minutes // 5

    return {
        "task": title,
        "time_available": minutes,
        "survival_probability": min(90, max(20, int(minutes / 2))),
        "steps": [
            {"step": 1, "title": "Understand requirements", "duration": max(step_time // 2, 5),
             "ai_help": "Paste the requirements — I'll extract the key points."},
            {"step": 2, "title": "Create outline/plan", "duration": step_time,
             "ai_help": "Tell me the topic — I'll generate a structure instantly."},
            {"step": 3, "title": "Core work — main content", "duration": step_time * 2,
             "ai_help": "Stuck? Send me what you have — I'll help you continue."},
            {"step": 4, "title": "Review and polish", "duration": step_time,
             "ai_help": "Paste your work — I'll check for gaps."},
            {"step": 5, "title": "Submit", "duration": max(step_time // 2, 5),
             "ai_help": None},
        ],
        "key_strategy": "Focus on completing, not perfecting.",
        "message": "Crisis plan ready! 🚨",
    }


# ═══════════════════════════════════════════════
# TOOL 6 — Procrastination Tracker
# ═══════════════════════════════════════════════

def procrastination_tracker_func(tasks: list) -> dict:
    """Analyze user's procrastination patterns from task history."""
    from ml.patterns import analyze_patterns
    return analyze_patterns(tasks)


# ═══════════════════════════════════════════════
# TOOL 7 — Email Drafter
# ═══════════════════════════════════════════════

def email_drafter_func(
    task_title: str,
    deadline: str = "",
    reason: str = "",
    recipient: str = "Professor",
    user_name: str = "Student",
) -> str:
    """Draft a professional extension request email."""
    prompt = f"""Draft a professional, polite email requesting a deadline extension.

Task: {task_title}
Original Deadline: {deadline}
Reason: {reason}
Recipient: {recipient}
Sender: {user_name}

Write a concise, respectful email that:
1. Has a clear subject line
2. States the request directly
3. Provides the reason without over-explaining
4. Suggests a new deadline (48 hours extension)
5. Shows commitment to quality work
6. Is professional but warm

Format as a complete email with Subject:, then the body."""

    return invoke_llm(prompt)


# ═══════════════════════════════════════════════
# TOOL 8 — Weekly Review Generator
# ═══════════════════════════════════════════════

def weekly_review_func(tasks: list, user_info: dict = None) -> dict:
    """Generate comprehensive weekly life review."""
    completed = [t for t in tasks if t.get("status") == "completed"]
    missed = [t for t in tasks if t.get("status") in ["overdue", "pending"]]
    total = len(tasks)

    completion_rate = len(completed) / max(total, 1)
    score = int(completion_rate * 100)

    wins = [t.get("title", "Unknown") for t in completed[:10]]
    losses = [t.get("title", "Unknown") for t in missed[:5]]

    streak = user_info.get("streak_days", 0) if user_info else 0

    return {
        "productivity_score": score,
        "completion_rate": round(completion_rate, 2),
        "wins": wins,
        "losses": losses,
        "streak_days": streak,
        "total_tasks": total,
        "completed": len(completed),
        "missed": len(missed),
    }


# ═══════════════════════════════════════════════
# TOOL 9 — Break Task Into Steps
# ═══════════════════════════════════════════════

def break_task_func(task: dict) -> list:
    """Break a big task into 25-minute Pomodoro micro-steps."""
    task_title = task.get("title", "Task")
    estimated_hours = task.get("estimated_hours", 2)
    category = task.get("category", "general")

    prompt = f"""Break this task into small, actionable 25-minute steps (Pomodoro technique).

Task: {task_title}
Category: {category}
Estimated Total Time: {estimated_hours} hours

Create {max(3, int(estimated_hours * 2.4))} steps, each ~25 minutes.
For each step, note if AI can assist.

Respond in valid JSON:
[
    {{"step": 1, "title": "step title", "duration_minutes": 25, "ai_can_help": true/false, "ai_help_description": "how AI helps or null"}},
    ...
]

Make steps specific and actionable, not vague."""

    try:
        response = invoke_llm(prompt)
        # Parse JSON
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]

        steps = json.loads(response.strip())
        return steps
    except Exception:
        # Template fallback
        n_steps = max(3, int(estimated_hours * 2))
        return [
            {"step": i+1, "title": f"Work on {task_title} — Part {i+1}",
             "duration_minutes": 25, "ai_can_help": True,
             "ai_help_description": "Send me what you're stuck on — I'll help."}
            for i in range(n_steps)
        ]


# ═══════════════════════════════════════════════
# TOOL 10 — Mood Aware Scheduler
# ═══════════════════════════════════════════════

def mood_aware_scheduler_func(mood: str, tasks: list) -> dict:
    """Restructure schedule based on user's current energy level."""
    ENERGY_REQUIREMENTS = {
        "academic": 3,   # High energy
        "career": 3,     # High energy
        "health": 2,     # Medium energy
        "personal": 1,   # Low energy
        "finance": 1,    # Low energy (usually quick tasks)
    }

    # Classify tasks by energy requirement
    for task in tasks:
        cat = task.get("category", "personal")
        task["energy_required"] = ENERGY_REQUIREMENTS.get(cat, 2)
        est = task.get("estimated_hours", 1)
        if est < 0.5:
            task["energy_required"] = max(1, task["energy_required"] - 1)

    if mood == "tired":
        # Easiest tasks first, breaks every 45 min, save hard tasks for later
        tasks.sort(key=lambda t: (t.get("energy_required", 2), -t.get("priority_score", 5)))
        schedule = schedule_builder_func(tasks, {
            "start": 9, "end": 21, "peak_start": 14, "peak_end": 17
        })
        schedule["mood_note"] = (
            "😴 Tired Mode: Starting with easy wins to build momentum. "
            "Hard tasks moved to afternoon when you'll have more energy."
        )
        schedule["break_frequency"] = "Every 45 minutes"

    elif mood == "energized":
        # Hardest tasks first, maximize peak hours
        tasks.sort(key=lambda t: (-t.get("energy_required", 2), -t.get("priority_score", 5)))
        schedule = schedule_builder_func(tasks, {
            "start": 9, "end": 21, "peak_start": 9, "peak_end": 13
        })
        schedule["mood_note"] = (
            "🔥 Energized Mode: Attacking the hardest tasks first! "
            "Maximum output while your energy is high."
        )
        schedule["break_frequency"] = "Every 90 minutes"

    elif mood == "stressed":
        # Micro-tasks, frequent breaks, quick wins first
        tasks.sort(key=lambda t: (t.get("estimated_hours", 1), -t.get("priority_score", 5)))
        schedule = schedule_builder_func(tasks, {
            "start": 9, "end": 21, "peak_start": 10, "peak_end": 12
        })
        # Add breathing exercise at the start
        schedule["schedule"].insert(0, {
            "time": "09:00",
            "task": "🧘 5-minute breathing exercise",
            "duration_minutes": 5,
            "category": "wellness",
            "type": "break",
        })
        schedule["mood_note"] = (
            "😰 Stress Mode: Starting with a breathing exercise, then quick wins. "
            "One small task at a time. You've got this."
        )
        schedule["break_frequency"] = "Every 30 minutes"

    elif mood == "distracted":
        # Very short blocks (15 min), frequent switches, timer-based
        tasks.sort(key=lambda t: (-t.get("priority_score", 5), t.get("estimated_hours", 1)))
        schedule = schedule_builder_func(tasks, {
            "start": 9, "end": 21, "peak_start": 9, "peak_end": 11
        })
        schedule["mood_note"] = (
            "😕 Focus Mode: Using 15-minute micro-blocks. "
            "Set a timer, work on ONE thing, then take a 3-minute break."
        )
        schedule["break_frequency"] = "Every 15 minutes (micro-breaks)"

    else:
        # Neutral — standard scheduling
        tasks.sort(key=lambda t: -t.get("priority_score", 5))
        schedule = schedule_builder_func(tasks)
        schedule["mood_note"] = "Standard scheduling — highest priority first."
        schedule["break_frequency"] = "Every 60 minutes"

    schedule["mood"] = mood
    return schedule


# ═══════════════════════════════════════════════
# LangChain Tool Definitions
# ═══════════════════════════════════════════════

def get_langchain_tools():
    """Create LangChain Tool objects for the agent."""
    from langchain.tools import Tool

    tools = [
        Tool(
            name="brain_dump_nlp",
            func=lambda text: json.dumps(brain_dump_nlp_func(text)),
            description=(
                "Extract structured tasks from messy, chaotic user input text. "
                "Input: raw text string. Output: JSON with extracted tasks, "
                "deadlines, categories, and urgency scores."
            ),
        ),
        Tool(
            name="priority_scorer",
            func=lambda tasks_json: json.dumps(priority_scorer_func(json.loads(tasks_json))),
            description=(
                "Score and rank tasks by urgency using ML model. "
                "Input: JSON array of tasks. Output: tasks sorted by priority score (0-10)."
            ),
        ),
        Tool(
            name="schedule_builder",
            func=lambda tasks_json: json.dumps(schedule_builder_func(json.loads(tasks_json))),
            description=(
                "Build an optimal daily schedule from prioritized tasks. "
                "Input: JSON array of tasks. Output: time-slotted schedule with breaks."
            ),
        ),
        Tool(
            name="conflict_detector",
            func=lambda schedule_json: json.dumps(conflict_detector_func(json.loads(schedule_json))),
            description=(
                "Find scheduling conflicts, overload, and energy issues. "
                "Input: JSON schedule object. Output: list of conflicts with suggestions."
            ),
        ),
        Tool(
            name="crisis_activator",
            func=lambda args: json.dumps(crisis_activator_func(
                json.loads(args).get("task", {}),
                json.loads(args).get("minutes", 60)
            )),
            description=(
                "Generate emergency battle plan for last-minute tasks. "
                "Input: JSON with 'task' object and 'minutes' available. "
                "Output: step-by-step survival plan with AI help options."
            ),
        ),
        Tool(
            name="procrastination_tracker",
            func=lambda tasks_json: json.dumps(procrastination_tracker_func(json.loads(tasks_json))),
            description=(
                "Analyze user's procrastination patterns from task history. "
                "Input: JSON array of user's tasks. Output: behavioral patterns and recommendations."
            ),
        ),
        Tool(
            name="email_drafter",
            func=lambda args: email_drafter_func(**json.loads(args)),
            description=(
                "Draft a professional deadline extension email. "
                "Input: JSON with task_title, deadline, reason, recipient, user_name. "
                "Output: complete professional email text."
            ),
        ),
        Tool(
            name="weekly_review",
            func=lambda tasks_json: json.dumps(weekly_review_func(json.loads(tasks_json))),
            description=(
                "Generate comprehensive weekly productivity review. "
                "Input: JSON array of user's tasks. Output: score, wins, misses, recommendations."
            ),
        ),
        Tool(
            name="break_task_into_steps",
            func=lambda task_json: json.dumps(break_task_func(json.loads(task_json))),
            description=(
                "Break a large task into 25-minute Pomodoro micro-steps. "
                "Input: JSON task object. Output: array of micro-steps with time estimates."
            ),
        ),
        Tool(
            name="mood_aware_scheduler",
            func=lambda args: json.dumps(mood_aware_scheduler_func(
                json.loads(args).get("mood", "neutral"),
                json.loads(args).get("tasks", [])
            )),
            description=(
                "Restructure daily plan based on user's current energy level. "
                "Input: JSON with 'mood' (tired|energized|stressed|distracted) and 'tasks' array. "
                "Output: mood-adjusted schedule."
            ),
        ),
    ]

    return tools
