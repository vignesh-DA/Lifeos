"""
LIFEOS NLP — Brain Dump Processing Engine
Transforms chaotic human text into structured tasks using spaCy.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Optional


# ─── Load spaCy ───
try:
    import spacy
    nlp = spacy.load("en_core_web_sm")
except Exception:
    nlp = None


# ─── Category Keywords ───
CATEGORY_KEYWORDS = {
    "academic": [
        "assignment", "exam", "test", "study", "homework", "class", "lecture",
        "professor", "submission", "project", "lab", "quiz", "research",
        "paper", "thesis", "presentation", "grade", "college", "university",
        "semester", "course", "tutorial", "report", "ml", "ai", "math",
        "physics", "chemistry", "biology", "programming", "code", "coding",
    ],
    "career": [
        "interview", "job", "resume", "cv", "application", "apply",
        "company", "internship", "work", "salary", "linkedin", "career",
        "portfolio", "networking", "meeting", "client", "boss", "manager",
        "promotion", "tcs", "infosys", "wipro", "google", "microsoft",
        "amazon", "placement", "recruitment", "hr", "offer",
    ],
    "finance": [
        "bill", "pay", "payment", "rent", "electricity", "water", "gas",
        "insurance", "emi", "loan", "credit", "bank", "money", "salary",
        "invest", "budget", "expense", "tax", "fee", "subscription",
        "gym", "membership", "recharge", "wifi", "phone",
    ],
    "personal": [
        "mom", "dad", "family", "friend", "birthday", "anniversary",
        "call", "visit", "gift", "wedding", "party", "dinner",
        "travel", "trip", "vacation", "shopping", "cook", "clean",
        "laundry", "grocery", "doctor", "dentist", "appointment",
    ],
    "health": [
        "gym", "exercise", "workout", "run", "yoga", "meditate",
        "sleep", "diet", "eat", "health", "doctor", "medicine",
        "vitamin", "weight", "fitness", "walk", "sport",
    ],
}

# ─── Deadline Keywords ───
DEADLINE_PATTERNS = {
    "today": 0,
    "tonight": 0,
    "tomorrow": 1,
    "day after tomorrow": 2,
    "this week": 5,
    "next week": 10,
    "this weekend": None,  # Calculated dynamically
    "monday": None,
    "tuesday": None,
    "wednesday": None,
    "thursday": None,
    "friday": None,
    "saturday": None,
    "sunday": None,
    "end of week": 5,
    "end of month": 30,
}

# ─── Urgency/Overdue Indicators ───
OVERDUE_INDICATORS = [
    "overdue", "late", "missed", "past due", "expired", "behind",
    "forgot", "forgotten", "neglected", "pending for", "haven't",
    "haven't done", "still haven't", "need to", "gotta",
]

STRESS_INDICATORS = [
    "stressed", "stress", "anxious", "anxiety", "overwhelmed", "panic",
    "freaking out", "scared", "worried", "nervous", "exhausted", "tired",
    "burned out", "burnout", "cooked", "dead", "dying", "help",
    "can't handle", "too much", "drowning", "losing it",
]

CONSEQUENCE_WEIGHTS = {
    "academic": 2.5,
    "career": 3.0,
    "finance": 2.8,
    "personal": 2.0,
    "health": 1.5,
}


def process_brain_dump(text: str) -> dict:
    """
    Main brain dump processing pipeline.
    Takes raw messy text → Returns structured tasks.
    """
    # Clean and normalize text
    text = text.strip()
    if not text:
        return {"tasks": [], "summary": "No text provided", "stress_level": "low"}

    # Detect stress level
    stress_level = _detect_stress(text)

    # Extract tasks using NLP + pattern matching
    tasks = _extract_tasks(text)

    # Score each task
    for task in tasks:
        task["urgency_score"] = _calculate_urgency(task)

    # Sort by urgency
    tasks.sort(key=lambda t: t["urgency_score"], reverse=True)

    # Identify immediate actions
    immediate = [t["title"] for t in tasks if t["urgency_score"] >= 9.0]

    # Build summary
    categories = {}
    for t in tasks:
        cat = t["category"]
        categories[cat] = categories.get(cat, 0) + 1

    cat_summary = ", ".join(f"{v} {k}" for k, v in categories.items())
    summary = f"{len(tasks)} tasks extracted. {cat_summary}."

    return {
        "tasks": tasks,
        "summary": summary,
        "stress_level": stress_level,
        "immediate_action_required": immediate,
        "total_estimated_hours": sum(t["estimated_hours"] for t in tasks),
    }


def _detect_stress(text: str) -> str:
    """Detect user's stress level from text."""
    text_lower = text.lower()
    stress_count = sum(1 for indicator in STRESS_INDICATORS if indicator in text_lower)

    if stress_count >= 3:
        return "critical"
    elif stress_count >= 2:
        return "high"
    elif stress_count >= 1:
        return "medium"
    return "low"


def _extract_tasks(text: str) -> list:
    """Extract individual tasks from raw text using NLP and patterns."""
    tasks = []

    # Split text into potential task segments
    # Split on commas, "and", periods, newlines, semicolons
    segments = re.split(r'[,;\n]+|(?:\band\b)', text)

    # Also try spaCy sentence segmentation if available
    if nlp:
        doc = nlp(text)
        spacy_sentences = [sent.text.strip() for sent in doc.sents]
        # Merge both approaches — use the one with more segments
        if len(spacy_sentences) > len(segments):
            segments = spacy_sentences

    seen_titles = set()

    for segment in segments:
        segment = segment.strip()
        if len(segment) < 5:
            continue

        # Skip segments that are just stress expressions
        if _is_just_stress(segment):
            continue

        # Extract task from segment
        task = _parse_segment(segment)
        if task and task["title"] not in seen_titles:
            seen_titles.add(task["title"])
            tasks.append(task)

    return tasks


def _is_just_stress(segment: str) -> bool:
    """Check if a segment is just a stress expression with no task."""
    lower = segment.lower().strip()
    # Very short segments that are just exclamations
    if len(lower) < 15:
        for indicator in STRESS_INDICATORS:
            if lower == indicator or lower.startswith(indicator):
                return True
    # Check if it's entirely a stress expression
    for indicator in STRESS_INDICATORS:
        if lower == indicator:
            return True
    return False


def _parse_segment(segment: str) -> Optional[dict]:
    """Parse a single text segment into a task."""
    segment_lower = segment.lower().strip()

    # Detect category
    category = _detect_category(segment_lower)

    # Detect deadline
    deadline, deadline_confidence = _detect_deadline(segment_lower)

    # Check if overdue
    is_overdue = any(ind in segment_lower for ind in OVERDUE_INDICATORS)

    # Generate clean title
    title = _generate_title(segment, category)
    if not title or len(title) < 3:
        return None

    # Estimate hours based on category
    estimated_hours = _estimate_hours(category, segment_lower)

    # Extract keywords
    keywords = _extract_keywords(segment_lower)

    return {
        "title": title,
        "deadline": deadline if deadline else ("overdue" if is_overdue else "unknown"),
        "deadline_confidence": deadline_confidence,
        "category": category,
        "urgency_score": 5.0,  # Will be recalculated
        "estimated_hours": estimated_hours,
        "extracted_keywords": keywords,
        "is_overdue": is_overdue,
    }


def _detect_category(text: str) -> str:
    """Detect task category from keywords."""
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[category] = score

    if scores:
        return max(scores, key=scores.get)
    return "personal"


def _detect_deadline(text: str) -> tuple[Optional[str], str]:
    """Detect deadline from text. Returns (date_string, confidence)."""
    now = datetime.now(timezone.utc)

    for pattern, days_offset in DEADLINE_PATTERNS.items():
        if pattern in text:
            if days_offset is not None:
                deadline_date = now + timedelta(days=days_offset)
                return deadline_date.strftime("%Y-%m-%d"), "high"
            else:
                # Handle day names
                if pattern in ["monday", "tuesday", "wednesday", "thursday",
                               "friday", "saturday", "sunday"]:
                    target_day = [
                        "monday", "tuesday", "wednesday", "thursday",
                        "friday", "saturday", "sunday"
                    ].index(pattern)
                    current_day = now.weekday()
                    days_ahead = (target_day - current_day) % 7
                    if days_ahead == 0:
                        days_ahead = 7  # Next occurrence
                    deadline_date = now + timedelta(days=days_ahead)
                    return deadline_date.strftime("%Y-%m-%d"), "high"

                elif pattern == "this weekend":
                    # Next Saturday
                    days_ahead = (5 - now.weekday()) % 7
                    if days_ahead == 0:
                        days_ahead = 1  # If Saturday, then Sunday
                    deadline_date = now + timedelta(days=days_ahead)
                    return deadline_date.strftime("%Y-%m-%d"), "medium"

    # Try to extract date-like patterns (e.g., "June 25", "25th")
    date_match = re.search(r'(\d{1,2})(st|nd|rd|th)?\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)?', text)
    if date_match:
        return None, "low"  # Found a date hint but can't parse reliably

    return None, "low"


def _generate_title(segment: str, category: str) -> str:
    """Generate a clean task title from a messy segment."""
    # Remove common filler words
    fillers = [
        "i need to", "i have to", "i gotta", "gotta", "need to",
        "have to", "should", "must", "gonna", "going to",
        "i'm", "im", "i am", "bro", "dude", "man",
        "like", "basically", "actually", "literally",
        "so ", "and ", "but ", "also ", "oh ",
    ]

    title = segment.strip()
    title_lower = title.lower()

    for filler in fillers:
        if title_lower.startswith(filler):
            title = title[len(filler):].strip()
            title_lower = title.lower()

    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    # Clean up
    title = re.sub(r'\s+', ' ', title).strip()

    # Remove trailing punctuation
    title = title.rstrip('.,;:!?')

    # Truncate if too long
    if len(title) > 80:
        title = title[:77] + "..."

    return title


def _estimate_hours(category: str, text: str) -> float:
    """Estimate hours needed based on category and text hints."""
    base_hours = {
        "academic": 3.0,
        "career": 2.0,
        "finance": 0.25,
        "personal": 0.5,
        "health": 1.0,
    }

    hours = base_hours.get(category, 1.0)

    # Adjust based on keywords
    if any(w in text for w in ["quick", "fast", "simple", "easy", "just"]):
        hours *= 0.5
    if any(w in text for w in ["big", "large", "major", "huge", "complex"]):
        hours *= 2.0
    if any(w in text for w in ["call", "email", "text", "message", "pay"]):
        hours = 0.25
    if any(w in text for w in ["project", "report", "thesis", "research"]):
        hours = max(hours, 4.0)
    if any(w in text for w in ["preparation", "prep", "prepare", "study"]):
        hours = max(hours, 2.0)

    return round(hours, 2)


def _extract_keywords(text: str) -> list:
    """Extract important keywords from text."""
    keywords = []

    if nlp:
        doc = nlp(text)
        # Get named entities
        for ent in doc.ents:
            keywords.append(ent.text)
        # Get nouns and proper nouns
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 2:
                if token.text.lower() not in ["thing", "stuff", "way", "time", "day"]:
                    keywords.append(token.text)
    else:
        # Fallback: just use important-looking words
        words = text.split()
        for word in words:
            word_clean = re.sub(r'[^\w]', '', word)
            if len(word_clean) > 3 and word_clean[0].isupper():
                keywords.append(word_clean)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for kw in keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique.append(kw)

    return unique[:10]  # Max 10 keywords


def _calculate_urgency(task: dict) -> float:
    """
    Calculate urgency score (0-10) using the formula:
    urgency = (deadline_proximity * 0.4) + (consequence_weight * 0.3)
              + (frequency_of_mention * 0.2) + (overdue_flag * 0.1)
    """
    now = datetime.now(timezone.utc)

    # Deadline proximity (0-10)
    deadline_score = 5.0
    deadline = task.get("deadline", "unknown")
    if deadline == "overdue":
        deadline_score = 10.0
    elif deadline and deadline not in ["unknown", "none"]:
        try:
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            hours_remaining = (deadline_date - now).total_seconds() / 3600
            if hours_remaining <= 0:
                deadline_score = 10.0
            elif hours_remaining <= 12:
                deadline_score = 9.5
            elif hours_remaining <= 24:
                deadline_score = 9.0
            elif hours_remaining <= 48:
                deadline_score = 8.0
            elif hours_remaining <= 72:
                deadline_score = 7.0
            elif hours_remaining <= 168:  # 1 week
                deadline_score = 5.0
            else:
                deadline_score = 3.0
        except (ValueError, TypeError):
            deadline_score = 5.0

    # Consequence weight (0-10)
    category = task.get("category", "personal")
    consequence_score = CONSEQUENCE_WEIGHTS.get(category, 2.0) * 3.33  # Scale to 0-10

    # Keyword frequency (simplified — 0-10)
    keyword_count = len(task.get("extracted_keywords", []))
    frequency_score = min(10.0, keyword_count * 2.0)

    # Overdue flag (0 or 10)
    overdue_score = 10.0 if task.get("is_overdue", False) else 0.0

    # Combined score
    urgency = (
        deadline_score * 0.4 +
        consequence_score * 0.3 +
        frequency_score * 0.2 +
        overdue_score * 0.1
    )

    return round(min(10.0, max(0.0, urgency)), 1)
