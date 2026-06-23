"""
LIFEOS NLP — Sentiment / Mood Analysis
Lightweight mood detection using pattern matching + optional LLM.
"""


MOOD_KEYWORDS = {
    "tired": [
        "tired", "exhausted", "sleepy", "fatigue", "drained", "worn out",
        "no energy", "can't focus", "drowsy", "lethargic", "burned out",
        "burnout", "sleep deprived", "need rest", "dead tired",
    ],
    "stressed": [
        "stressed", "stress", "anxious", "anxiety", "overwhelmed", "panic",
        "worried", "nervous", "tense", "pressure", "deadline", "too much",
        "can't handle", "freaking out", "losing it", "cooked", "doomed",
    ],
    "energized": [
        "energized", "motivated", "pumped", "excited", "ready", "fresh",
        "productive", "focused", "charged", "great mood", "feeling good",
        "let's go", "bring it on", "on fire", "unstoppable",
    ],
    "distracted": [
        "distracted", "unfocused", "scattered", "can't concentrate",
        "mind wandering", "procrastinating", "bored", "restless",
        "sidetracked", "lost", "confused", "all over the place",
    ],
}


def detect_mood(text: str) -> dict:
    """
    Detect user's current mood from text input.
    Returns mood label + confidence + detected indicators.
    """
    text_lower = text.lower()

    scores = {}
    detected_keywords = {}

    for mood, keywords in MOOD_KEYWORDS.items():
        matches = [kw for kw in keywords if kw in text_lower]
        scores[mood] = len(matches)
        if matches:
            detected_keywords[mood] = matches

    if not any(scores.values()):
        return {
            "mood": "neutral",
            "confidence": 0.5,
            "detected_indicators": [],
            "suggestion": "How are you feeling right now? Select your mood above.",
        }

    # Get the dominant mood
    dominant_mood = max(scores, key=scores.get)
    max_score = scores[dominant_mood]
    total_matches = sum(scores.values())
    confidence = round(max_score / max(total_matches, 1), 2)

    # Generate suggestion based on mood
    suggestions = {
        "tired": "I've adjusted your schedule to start with easier tasks. Take breaks every 45 minutes.",
        "stressed": "Let's start with one small win. I've put the quickest task first to build momentum.",
        "energized": "Great energy! I've front-loaded your hardest tasks to maximize this momentum.",
        "distracted": "I've broken your tasks into 15-minute micro-blocks. One thing at a time.",
    }

    return {
        "mood": dominant_mood,
        "confidence": confidence,
        "detected_indicators": detected_keywords.get(dominant_mood, []),
        "all_scores": scores,
        "suggestion": suggestions.get(dominant_mood, ""),
    }


def detect_mood_from_emoji(emoji: str) -> str:
    """Map emoji mood selector to mood string."""
    emoji_map = {
        "😴": "tired",
        "😰": "stressed",
        "🔥": "energized",
        "😕": "distracted",
    }
    return emoji_map.get(emoji, "neutral")
