"""
LIFEOS Routes — Analytics & Insights Endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from db.mongodb import tasks_collection, patterns_collection, users_collection, reviews_collection

router = APIRouter()


class ReviewRequest(BaseModel):
    user_id: str
    week: str = ""  # e.g., "2026-W25"


@router.get("/insights/{user_id}")
async def get_insights(user_id: str):
    """
    Get ML-powered insights, patterns, and recommendations for a user.
    Combines procrastination patterns + productivity analysis.
    """
    try:
        from ml.patterns import analyze_patterns
        from db.mongodb import tasks_collection

        # Get all user tasks
        cursor = tasks_collection().find({"user_id": user_id})
        tasks = []
        async for task in cursor:
            task["_id"] = str(task["_id"])
            tasks.append(task)

        if not tasks:
            return {
                "user_id": user_id,
                "patterns": {
                    "most_avoided_category": "none",
                    "best_productivity_hour": 9,
                    "worst_productivity_hour": 15,
                    "avg_procrastination_days": 0,
                    "peak_day": "Monday",
                    "completion_rate": 0,
                    "procrastination_triggers": [],
                    "strongest_categories": [],
                },
                "recommendations": [
                    "Start adding tasks to see personalized insights!",
                    "Use brain dump to capture everything on your mind.",
                    "Complete tasks consistently to build your streak.",
                ],
                "charts_data": _empty_charts_data(),
                "intervention_needed": False,
                "message": "No data yet — start adding tasks to unlock insights! 📊",
            }

        # Analyze patterns
        insights = analyze_patterns(tasks)

        # Generate chart data
        charts_data = _generate_charts_data(tasks)

        return {
            "user_id": user_id,
            "patterns": insights.get("patterns", {}),
            "recommendations": insights.get("recommendations", []),
            "charts_data": charts_data,
            "intervention_needed": insights.get("intervention_needed", False),
            "intervention_message": insights.get("intervention_message", ""),
            "message": "Insights generated successfully 🧠",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")


@router.post("/review/generate")
async def generate_review(request: ReviewRequest):
    """
    Generate a comprehensive weekly life review using all data.
    Includes productivity score, wins, misses, patterns, and next week plan.
    """
    from datetime import datetime, timezone

    # Determine week
    week = request.week
    if not week:
        now = datetime.now(timezone.utc)
        week = f"{now.year}-W{now.isocalendar()[1]:02d}"

    try:
        # Get all tasks for this user
        cursor = tasks_collection().find({"user_id": request.user_id})
        tasks = []
        async for task in cursor:
            task["_id"] = str(task["_id"])
            tasks.append(task)

        completed = [t for t in tasks if t.get("status") == "completed"]
        missed = [t for t in tasks if t.get("status") in ["overdue", "pending"]]
        total = len(tasks)

        # Calculate scores
        completion_rate = len(completed) / max(total, 1)
        productivity_score = int(completion_rate * 100)

        # Get user streak info
        user = await users_collection().find_one({"user_id": request.user_id})
        streak = user.get("streak_days", 0) if user else 0
        best_streak = user.get("best_streak", 0) if user else 0

        # Build review
        wins = [f"{t['title']}" for t in completed[:10]]
        losses = [f"{t['title']}" for t in missed[:5]]

        # Generate recommendations
        recommendations = []
        if completion_rate < 0.5:
            recommendations.append("Try breaking large tasks into smaller steps — use the 'Break Down' feature.")
        if any(t.get("postpone_count", 0) >= 3 for t in tasks):
            most_postponed = max(tasks, key=lambda t: t.get("postpone_count", 0))
            recommendations.append(
                f"'{most_postponed['title']}' has been postponed {most_postponed['postpone_count']} times. "
                f"Try scheduling it during your peak hours."
            )
        if streak > 0:
            recommendations.append(f"Keep your {streak}-day streak alive! 🔥")

        # Check for badges
        badges = []
        if completion_rate >= 0.9:
            badges.append("🏆 Perfectionist!")
        if streak >= 7:
            badges.append("⚡ Week Warrior!")
        if len(completed) >= 20:
            badges.append("💪 Productivity Machine!")

        review = {
            "user_id": request.user_id,
            "week": week,
            "productivity_score": productivity_score,
            "completion_rate": round(completion_rate, 2),
            "total_tasks": total,
            "completed_count": len(completed),
            "missed_count": len(missed),
            "wins": wins,
            "losses": losses,
            "streak_days": streak,
            "best_streak": best_streak,
            "badges": badges,
            "next_week_focus": recommendations[0] if recommendations else "Keep up the great work!",
            "recommendations": recommendations,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Save review to MongoDB
        await reviews_collection().update_one(
            {"user_id": request.user_id, "week": week},
            {"$set": review},
            upsert=True,
        )

        return {
            "review": review,
            "message": f"Weekly review for {week} generated! 📈",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Review generation failed: {str(e)}")


@router.get("/review/current/{user_id}")
async def get_current_review(user_id: str):
    """
    Get the weekly review for the current week, if it exists in the database.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    week = f"{now.year}-W{now.isocalendar()[1]:02d}"

    try:
        review = await reviews_collection().find_one({"user_id": user_id, "week": week})
        if review:
            review["_id"] = str(review["_id"])
            return {"review": review, "exists": True}
        return {"review": None, "exists": False}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch review: {str(e)}")


def _generate_charts_data(tasks: list) -> dict:
    """Generate data formatted for Chart.js charts."""
    from collections import Counter, defaultdict
    from datetime import datetime, timezone, timedelta

    # Category distribution
    categories = Counter(t.get("category", "personal") for t in tasks)

    # Status distribution
    statuses = Counter(t.get("status", "pending") for t in tasks)

    # Completion by category
    completed_by_cat = Counter(
        t.get("category", "personal")
        for t in tasks if t.get("status") == "completed"
    )

    # Hour-by-hour productivity from task creation times
    hour_counts: dict = defaultdict(int)
    for task in tasks:
        created = task.get("created_at")
        if created:
            try:
                if isinstance(created, str):
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                else:
                    dt = created
                hour_counts[str(dt.hour)] += 1
            except Exception:
                pass
    hour_productivity = {str(h): hour_counts.get(str(h), 0) for h in range(24)}

    # Weekly productivity — compute from completion rates per week
    now = datetime.now(timezone.utc)
    weekly_scores = []
    for weeks_ago in range(3, -1, -1):  # 4 weeks, oldest first
        week_start = now - timedelta(weeks=weeks_ago + 1)
        week_end = now - timedelta(weeks=weeks_ago)
        week_tasks = []
        week_completed = []
        for t in tasks:
            created = t.get("created_at")
            if created:
                try:
                    if isinstance(created, str):
                        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    else:
                        dt = created if dt.tzinfo else created.replace(tzinfo=timezone.utc)
                    if week_start <= dt <= week_end:
                        week_tasks.append(t)
                        if t.get("status") == "completed":
                            week_completed.append(t)
                except Exception:
                    pass
        if week_tasks:
            score = int((len(week_completed) / len(week_tasks)) * 100)
        else:
            # Fallback: use overall completion rate with slight variation
            total = len(tasks) or 1
            done = sum(1 for t in tasks if t.get("status") == "completed")
            base = int((done / total) * 100)
            score = max(10, base - (3 - weeks_ago) * 5)  # ramp up over weeks
        weekly_scores.append(min(100, score))

    return {
        "category_distribution": dict(categories),
        "status_distribution": dict(statuses),
        "completed_by_category": dict(completed_by_cat),
        "weekly_productivity": weekly_scores,
        "hour_productivity": hour_productivity,
    }


def _empty_charts_data() -> dict:
    """Return empty chart data structure."""
    return {
        "category_distribution": {},
        "status_distribution": {},
        "completed_by_category": {},
        "weekly_productivity": [0, 0, 0, 0],
        "hour_productivity": {str(h): 0 for h in range(24)},
    }
