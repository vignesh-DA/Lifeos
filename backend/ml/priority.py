"""
LIFEOS ML — Priority Scoring Model
scikit-learn model that scores task urgency 0.0 to 10.0.
"""
import os
import numpy as np
import joblib
from datetime import datetime, timezone

# ─── Feature Engineering ───

CATEGORY_ENCODING = {
    "personal": 0,
    "academic": 1,
    "career": 2,
    "finance": 3,
    "health": 4,
}

# Global model reference
_model = None
_model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "priority_model.pkl")


def generate_synthetic_data(n_samples: int = 500) -> tuple:
    """
    Generate synthetic training data for priority model.

    Feature vector per task:
    [0] deadline_hours_remaining  (0-720 hours = 30 days)
    [1] category_encoded          (0-4)
    [2] estimated_hours           (0.25-20)
    [3] postpone_count            (0-10)
    [4] time_of_day               (0-23)
    [5] user_peak_hour_match      (0 or 1)
    [6] overdue_flag              (0 or 1)
    [7] consequence_weight        (1-3)
    """
    np.random.seed(42)

    X = np.zeros((n_samples, 8))
    y = np.zeros(n_samples)

    for i in range(n_samples):
        # Generate features
        deadline_hours = np.random.exponential(72)  # Mostly near-term
        deadline_hours = min(deadline_hours, 720)
        category = np.random.randint(0, 5)
        estimated_hours = np.random.choice([0.25, 0.5, 1, 2, 3, 4, 6, 8, 12])
        postpone_count = np.random.poisson(1.5)
        postpone_count = min(postpone_count, 10)
        time_of_day = np.random.randint(6, 24)
        peak_match = np.random.choice([0, 1], p=[0.7, 0.3])
        overdue = 1 if deadline_hours <= 0 or np.random.random() < 0.15 else 0
        if overdue:
            deadline_hours = 0

        consequence = np.random.choice([1, 2, 3], p=[0.3, 0.4, 0.3])
        # Career and finance tend to be higher consequence
        if category in [2, 3]:
            consequence = max(consequence, 2)

        X[i] = [
            deadline_hours, category, estimated_hours, postpone_count,
            time_of_day, peak_match, overdue, consequence
        ]

        # Calculate target priority score
        # Higher priority = closer deadline + more postponed + overdue + high consequence
        deadline_factor = max(0, 10 - (deadline_hours / 72) * 10)  # 0-10
        postpone_factor = min(10, postpone_count * 2)  # 0-10
        overdue_factor = overdue * 10  # 0 or 10
        consequence_factor = consequence * 3.33  # ~3.3-10
        peak_bonus = peak_match * 1.5

        score = (
            deadline_factor * 0.35 +
            consequence_factor * 0.25 +
            postpone_factor * 0.20 +
            overdue_factor * 0.10 +
            peak_bonus * 0.05 +
            np.random.normal(0, 0.5) * 0.05  # Noise
        )

        y[i] = np.clip(score, 0, 10)

    return X, y


def train_model():
    """Train the priority scoring model and save to disk."""
    from sklearn.ensemble import GradientBoostingRegressor

    print("  🧠 Training priority scoring model...")
    X, y = generate_synthetic_data(500)

    model = GradientBoostingRegressor(
        n_estimators=100,
        max_depth=5,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X, y)

    # Save model
    joblib.dump(model, _model_path)
    print(f"  ✅ Model saved to {_model_path}")

    return model


def load_priority_model():
    """Load the trained model, or train a new one if not found."""
    global _model

    if os.path.exists(_model_path):
        _model = joblib.load(_model_path)
        print(f"  ✅ Loaded priority model from {_model_path}")
    else:
        _model = train_model()

    return _model


def predict_priority(task: dict) -> float:
    """
    Predict priority score (0.0-10.0) for a single task.

    Args:
        task: dict with keys like category, deadline, estimated_hours, etc.
    Returns:
        float: priority score 0.0 to 10.0
    """
    global _model
    if _model is None:
        try:
            load_priority_model()
        except Exception:
            return _fallback_priority(task)

    now = datetime.now(timezone.utc)

    # Extract features
    deadline_hours = 168  # Default: 1 week
    deadline = task.get("deadline")
    if deadline and deadline not in ["unknown", "overdue", "none", ""]:
        try:
            deadline_dt = datetime.strptime(str(deadline)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            deadline_hours = max(0, (deadline_dt - now).total_seconds() / 3600)
        except (ValueError, TypeError):
            pass

    category_encoded = CATEGORY_ENCODING.get(task.get("category", "personal"), 0)
    estimated_hours = task.get("estimated_hours", 1.0)
    postpone_count = task.get("postpone_count", 0)
    time_of_day = now.hour
    peak_match = 1 if time_of_day in range(9, 12) else 0  # Default peak: 9-11 AM
    overdue = 1 if deadline_hours <= 0 or task.get("deadline") == "overdue" else 0
    consequence = {"personal": 1, "health": 1, "academic": 2, "finance": 3, "career": 3}.get(
        task.get("category", "personal"), 2
    )

    features = np.array([[
        deadline_hours, category_encoded, estimated_hours, postpone_count,
        time_of_day, peak_match, overdue, consequence
    ]])

    score = float(_model.predict(features)[0])
    return round(np.clip(score, 0.0, 10.0), 1)


def predict_priorities(tasks: list) -> list:
    """Score multiple tasks and return them sorted by priority."""
    scored = []
    for task in tasks:
        score = predict_priority(task)
        task_copy = dict(task)
        task_copy["priority_score"] = score
        scored.append(task_copy)

    scored.sort(key=lambda t: t["priority_score"], reverse=True)
    return scored


def _fallback_priority(task: dict) -> float:
    """Simple fallback scoring without ML model."""
    score = 5.0

    deadline = task.get("deadline", "unknown")
    if deadline == "overdue":
        score += 4.0
    elif deadline == "today" or deadline == "tonight":
        score += 3.5

    category = task.get("category", "personal")
    if category in ["career", "finance"]:
        score += 1.5
    elif category == "academic":
        score += 1.0

    postpone = task.get("postpone_count", 0)
    score += min(postpone * 0.5, 2.0)

    return round(min(10.0, score), 1)
