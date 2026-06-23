"""
LIFEOS ML — Behavioral Pattern Analysis
Tracks and analyzes user's procrastination and productivity patterns.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional


def analyze_patterns(tasks: list) -> dict:
    """
    Analyze user's task history to detect behavioral patterns.

    Args:
        tasks: List of task dicts from MongoDB

    Returns:
        dict with patterns, recommendations, and intervention flags
    """
    if not tasks:
        return _empty_patterns()

    completed = [t for t in tasks if t.get("status") == "completed"]
    pending = [t for t in tasks if t.get("status") == "pending"]
    overdue = [t for t in tasks if t.get("status") == "overdue"]

    total = len(tasks)
    completion_rate = len(completed) / max(total, 1)

    # ─── Category Analysis ───
    category_counts = Counter(t.get("category", "personal") for t in tasks)
    completed_by_cat = Counter(t.get("category", "personal") for t in completed)
    pending_by_cat = Counter(t.get("category", "personal") for t in pending)

    # Find most avoided category (lowest completion rate)
    cat_completion_rates = {}
    for cat in category_counts:
        total_in_cat = category_counts[cat]
        completed_in_cat = completed_by_cat.get(cat, 0)
        cat_completion_rates[cat] = completed_in_cat / max(total_in_cat, 1)

    most_avoided = min(cat_completion_rates, key=cat_completion_rates.get) if cat_completion_rates else "none"
    strongest_cats = sorted(cat_completion_rates, key=cat_completion_rates.get, reverse=True)[:2]

    # ─── Postponement Analysis ───
    postpone_counts = [t.get("postpone_count", 0) for t in tasks]
    avg_procrastination = sum(postpone_counts) / max(len(postpone_counts), 1)

    # Find frequently postponed tasks
    chronic_postponers = [
        t.get("title", "Unknown")
        for t in tasks
        if t.get("postpone_count", 0) >= 3
    ]

    # ─── Procrastination Triggers (keywords from avoided tasks) ───
    avoided_keywords = []
    for t in tasks:
        if t.get("postpone_count", 0) >= 2:
            avoided_keywords.extend(t.get("tags", []))
            # Also extract words from title
            title_words = t.get("title", "").lower().split()
            avoided_keywords.extend([w for w in title_words if len(w) > 3])

    trigger_counts = Counter(avoided_keywords)
    procrastination_triggers = [word for word, _ in trigger_counts.most_common(5)]

    # ─── Time Analysis ───
    # Determine best/worst productivity hours from completed tasks
    completion_hours = []
    for t in completed:
        completed_at = t.get("completed_at")
        if completed_at:
            try:
                dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                completion_hours.append(dt.hour)
            except (ValueError, TypeError):
                pass

    best_hour = 9  # Default
    worst_hour = 15  # Default
    if completion_hours:
        hour_counts = Counter(completion_hours)
        best_hour = hour_counts.most_common(1)[0][0]
        # Worst hour = hour with least completions (during waking hours)
        for h in range(6, 24):
            if hour_counts.get(h, 0) == 0:
                worst_hour = h
                break

    # ─── Day Analysis ───
    completion_days = []
    for t in completed:
        completed_at = t.get("completed_at")
        if completed_at:
            try:
                dt = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
                completion_days.append(dt.strftime("%A"))
            except (ValueError, TypeError):
                pass

    peak_day = "Monday"  # Default
    if completion_days:
        day_counts = Counter(completion_days)
        peak_day = day_counts.most_common(1)[0][0]

    # ─── Generate Recommendations ───
    recommendations = _generate_recommendations(
        most_avoided=most_avoided,
        best_hour=best_hour,
        avg_procrastination=avg_procrastination,
        chronic_postponers=chronic_postponers,
        completion_rate=completion_rate,
        peak_day=peak_day,
    )

    # ─── Intervention Check ───
    intervention_needed = (
        completion_rate < 0.4 or
        avg_procrastination > 3 or
        len(chronic_postponers) >= 3
    )

    intervention_message = ""
    if intervention_needed:
        if completion_rate < 0.4:
            intervention_message = f"Your completion rate is {int(completion_rate*100)}%. Let's break tasks into smaller steps."
        elif len(chronic_postponers) >= 3:
            intervention_message = f"You've been avoiding {len(chronic_postponers)} tasks repeatedly. Let's tackle the easiest one right now."
        else:
            intervention_message = f"You've avoided {most_avoided} tasks for a while. I've scheduled them during your peak hours."

    return {
        "patterns": {
            "most_avoided_category": most_avoided,
            "best_productivity_hour": best_hour,
            "worst_productivity_hour": worst_hour,
            "avg_procrastination_days": round(avg_procrastination, 1),
            "peak_day": peak_day,
            "completion_rate": round(completion_rate, 2),
            "procrastination_triggers": procrastination_triggers,
            "strongest_categories": strongest_cats,
            "total_tasks": total,
            "completed_count": len(completed),
            "pending_count": len(pending),
            "overdue_count": len(overdue),
            "chronic_postponers": chronic_postponers[:5],
            "category_completion_rates": {
                k: round(v, 2) for k, v in cat_completion_rates.items()
            },
        },
        "recommendations": recommendations,
        "intervention_needed": intervention_needed,
        "intervention_message": intervention_message,
    }


def _generate_recommendations(
    most_avoided: str,
    best_hour: int,
    avg_procrastination: float,
    chronic_postponers: list,
    completion_rate: float,
    peak_day: str,
) -> list:
    """Generate personalized recommendations based on patterns."""
    recs = []

    if most_avoided != "none":
        recs.append(
            f"Schedule {most_avoided} tasks before {best_hour + 2}:00 — "
            f"you finish them {int(1/max(0.1, 1-completion_rate))}x faster in the morning."
        )

    if chronic_postponers:
        worst = chronic_postponers[0]
        recs.append(
            f"You've postponed '{worst}' multiple times — break it into 15-min sessions."
        )

    if peak_day:
        recs.append(
            f"Your {peak_day} productivity is highest — front-load hard tasks that day."
        )

    if completion_rate >= 0.7:
        recs.append("Great momentum! Keep your streak alive by tackling one task first thing tomorrow.")
    elif completion_rate >= 0.5:
        recs.append("You're halfway there. Try the 2-minute rule: if it takes less than 2 minutes, do it now.")
    else:
        recs.append("Start with just ONE easy task today. Small wins build momentum.")

    if avg_procrastination > 2:
        recs.append(
            f"You postpone tasks an average of {avg_procrastination:.1f} times. "
            f"Try the 'just 5 minutes' technique — start and you'll usually keep going."
        )

    return recs[:5]  # Max 5 recommendations


def _empty_patterns() -> dict:
    """Return empty patterns structure."""
    return {
        "patterns": {
            "most_avoided_category": "none",
            "best_productivity_hour": 9,
            "worst_productivity_hour": 15,
            "avg_procrastination_days": 0,
            "peak_day": "Monday",
            "completion_rate": 0,
            "procrastination_triggers": [],
            "strongest_categories": [],
            "total_tasks": 0,
            "completed_count": 0,
            "pending_count": 0,
            "overdue_count": 0,
        },
        "recommendations": ["Start adding tasks to unlock personalized insights!"],
        "intervention_needed": False,
        "intervention_message": "",
    }
