"""
LIFEOS — Google APIs Integration Helper
Uses raw httpx calls to interface with Google Calendar & Gmail APIs with auto-refreshing OAuth tokens.
"""
import time
import base64
import httpx
from config import settings
from db.mongodb import get_db


class GoogleAuthError(Exception):
    """Raised when a user's Google OAuth token is missing, expired, or revoked."""
    pass


async def get_google_access_token(user_id: str, required_scope: str) -> str:
    """
    Load user from DB, check if token is valid for required_scope,
    refresh if expired, and return a valid access token.

    Raises GoogleAuthError on every failure path so callers receive a typed
    exception instead of a silent None — letting them decide what "no token" means.
    """
    db = get_db()
    user = await db["users"].find_one({"google_id": user_id})
    if not user or "google_tokens" not in user:
        raise GoogleAuthError(f"No google_tokens found for user: {user_id}")

    tokens = user["google_tokens"]
    scopes = tokens.get("scopes", [])

    # Check if authorized for required scope
    if required_scope not in scopes:
        raise GoogleAuthError(
            f"Required scope '{required_scope}' not granted for user: {user_id}. "
            "User must re-authenticate."
        )

    access_token = tokens.get("access_token")
    expires_at   = tokens.get("expires_at", 0)
    refresh_token = tokens.get("refresh_token")

    # Token still valid (60-second margin)
    if access_token and expires_at > time.time() + 60:
        return access_token

    # Token expired — try refresh
    if not refresh_token:
        raise GoogleAuthError(
            f"Access token expired and no refresh_token available for user: {user_id}. "
            "User must re-authenticate."
        )

    print(f"  🔄 Refreshing Google access token for user: {user_id}...")
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10.0,
            )
            data = res.json()

            if "error" in data:
                raise GoogleAuthError(
                    f"Google token refresh failed for user {user_id}: {data.get('error_description', data)}"
                )

            new_access_token = data.get("access_token")
            expires_in       = data.get("expires_in", 3600)
            new_expires_at   = int(time.time()) + expires_in

            tokens["access_token"] = new_access_token
            tokens["expires_at"]   = new_expires_at

            await db["users"].update_one(
                {"google_id": user_id},
                {"$set": {"google_tokens": tokens}},
            )
            print(f"  ✅ Access token successfully refreshed for user: {user_id}")
            return new_access_token

    except GoogleAuthError:
        raise  # Don't swallow typed auth errors
    except Exception as e:
        raise GoogleAuthError(f"Unexpected error refreshing token for user {user_id}: {e}") from e


async def create_calendar_event(user_id: str, task: dict) -> str | None:
    """
    Create a scheduled event on Google Calendar for a task.

    - Returns the Google Calendar event_id (str) on success.
    - Returns None if the task has no valid deadline (skip, don't error).
    - Raises GoogleAuthError if OAuth is broken so the scheduler can log it
      distinctly and avoid retrying on every 5-minute tick.
    - Uses find_one_and_update with a 'pending' sentinel for an atomic
      check-and-set lock: whichever concurrent scheduler run claims the slot
      first proceeds to the API; the others bail out immediately.
      On API failure the sentinel is $unset so the next run can retry.
    """
    from datetime import datetime, timezone, timedelta
    from db.mongodb import tasks_collection
    from bson import ObjectId

    scope = "https://www.googleapis.com/auth/calendar.events"

    # ── 1. Validate deadline — skip rather than error on bad/missing values ───
    deadline_str = task.get("deadline")
    if not deadline_str or deadline_str in ("unknown", "overdue"):
        print(f"  ⏭️  Skipping calendar sync for '{task.get('title')}': no valid deadline.")
        return None

    now = datetime.now(timezone.utc)
    try:
        dl_dt = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        if dl_dt.tzinfo is None:
            dl_dt = dl_dt.replace(tzinfo=timezone.utc)
    except Exception:
        print(f"  ⏭️  Skipping calendar sync for '{task.get('title')}': unparseable deadline '{deadline_str}'.")
        return None

    # Focus block = 4 hours before deadline; if that's already past, 30 min from now
    target_start = dl_dt - timedelta(hours=4)
    if target_start < now:
        target_start = now + timedelta(minutes=30)
    start_time = target_start
    end_time   = start_time + timedelta(hours=task.get("estimated_hours", 1.0))

    # ── 2. Atomic check-and-set with a 'pending' sentinel ────────────────────
    # find_one_and_update is a single atomic op in MongoDB. Only the first
    # concurrent caller whose filter matches (field absent) will get a doc back;
    # all other concurrent callers will find the field already set to 'pending'
    # (or the real id) and return None → they bail out immediately, no duplicate.
    task_id_raw = task.get("_id")
    task_oid    = ObjectId(task_id_raw) if isinstance(task_id_raw, str) else task_id_raw

    if task_oid:
        claimed = await tasks_collection().find_one_and_update(
            {"_id": task_oid, "google_calendar_event_id": {"$exists": False}},
            {"$set": {"google_calendar_event_id": "pending"}},
            return_document=False,  # return the doc BEFORE the update
        )
        if claimed is None:
            # Another run already claimed or completed this task's slot.
            existing = await tasks_collection().find_one({"_id": task_oid})
            existing_id = existing.get("google_calendar_event_id") if existing else None
            if existing_id and existing_id != "pending":
                print(f"  ✅ Already synced '{task.get('title')}' (event {existing_id}) — skipping.")
                return existing_id
            # Still 'pending' from another in-flight run — skip this cycle
            print(f"  ⏳ Calendar sync for '{task.get('title')}' already in progress — skipping.")
            return None

    # ── 3. Auth — GoogleAuthError bubbles up uncaught to the scheduler ────────
    # get_google_access_token now raises GoogleAuthError on every failure path.
    token = await get_google_access_token(user_id, scope)

    title       = task.get("title", "LIFEOS Focus Session")
    description = task.get("description", "")
    priority    = task.get("priority_score", 5.0)

    start_str = start_time.isoformat()
    end_str   = end_time.isoformat()

    # ── 4. Explicit reminders — never rely on useDefault ─────────────────────
    # 'popup' is what triggers mobile push notifications via the Google Calendar app.
    if priority >= 8.0:       # URGENT
        reminder_overrides = [
            {"method": "popup", "minutes": 120},
            {"method": "popup", "minutes": 30},
            {"method": "email", "minutes": 15},
        ]
        color_id = "11"  # Red/Tomato
    elif priority >= 5.0:     # MEDIUM
        reminder_overrides = [
            {"method": "popup", "minutes": 60},
            {"method": "popup", "minutes": 15},
        ]
        color_id = "5"   # Yellow/Banana
    else:                     # LOW
        reminder_overrides = [
            {"method": "popup", "minutes": 30},
        ]
        color_id = "2"   # Green/Sage

    event_payload = {
        "summary": f"🎯 LIFEOS: {title}",
        "description": (
            f"Focus Block generated by LIFEOS.\n\n"
            f"Description: {description}\n"
            f"Priority Score: {priority}/10"
        ),
        "start": {"dateTime": start_str, "timeZone": "UTC"},
        "end":   {"dateTime": end_str,   "timeZone": "UTC"},
        "colorId": color_id,
        "reminders": {
            "useDefault": False,           # MUST be False — never trust user defaults
            "overrides": reminder_overrides,
        },
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=event_payload,
                timeout=10.0,
            )

        # 401 → raise so scheduler logs it as auth-broken, not transient
        if res.status_code == 401:
            if task_oid:
                await tasks_collection().update_one(
                    {"_id": task_oid},
                    {"$unset": {"google_calendar_event_id": ""}},
                )
            raise GoogleAuthError(
                f"Google CalendAar API 401 for user '{user_id}' — token invalid. "
                "User must re-authenticate."
            )

        if res.status_code not in (200, 201):
            # Transient failure — $unset sentinel so next run can retry
            if task_oid:
                await tasks_collection().update_one(
                    {"_id": task_oid},
                    {"$unset": {"google_calendar_event_id": ""}},
                )
            print(f"  ❌ Calendar API error {res.status_code} for '{title}': {res.text}")
            return None

        event_data = res.json()
        event_id   = event_data.get("id")
        print(f"  📅 Calendar event created: {event_id} for '{title}'")

        # ── 5. Replace 'pending' sentinel with the real event_id ─────────────
        if task_oid and event_id:
            try:
                await tasks_collection().update_one(
                    {"_id": task_oid},
                    {"$set": {"google_calendar_event_id": event_id}},
                )
                print(f"  💾 Persisted google_calendar_event_id '{event_id}' → task {task_oid}")
            except Exception as db_err:
                print(f"  ⚠️ Could not persist event_id to DB: {db_err}")

        return event_id

    except GoogleAuthError:
        raise  # Let caller (scheduler) handle auth errors distinctly
    except Exception as e:
        # Unexpected failure — $unset sentinel so the next run can retry
        if task_oid:
            try:
                await tasks_collection().update_one(
                    {"_id": task_oid},
                    {"$unset": {"google_calendar_event_id": ""}},
                )
            except Exception:
                pass
        print(f"  ❌ Unexpected error creating calendar event for '{title}': {e}")
        return None


async def delete_calendar_event(user_id: str, event_id: str) -> bool:
    """
    Delete a scheduled event from Google Calendar.
    """
    if not event_id:
        return False

    scope = "https://www.googleapis.com/auth/calendar.events"
    token = await get_google_access_token(user_id, scope)
    if not token:
        print("  ⚠️ Google OAuth token not available for calendar deletion.")
        return False

    try:
        async with httpx.AsyncClient() as client:
            res = await client.delete(
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            if res.status_code in [200, 204]:
                print(f"  📅 Calendar event successfully deleted: {event_id}")
                return True
            else:
                print(f"  ❌ Failed to delete calendar event: {res.status_code} - {res.text}")
                return False

    except Exception as e:
        print(f"  ❌ Error calling Google Calendar API for deletion: {e}")
        return False



async def create_gmail_draft(user_id: str, to: str, subject: str, body: str) -> dict | None:
    """
    Create a compose draft in user's Gmail drafts folder.
    Returns the draft dict on success, or None if auth is missing/broken
    or the API call fails — never raises, so callers can always check the
    return value without needing their own try/except for auth errors.
    """
    scope = "https://www.googleapis.com/auth/gmail.compose"
    try:
        token = await get_google_access_token(user_id, scope)
    except GoogleAuthError as e:
        # Auth missing or expired — log clearly and return None so the
        # caller (scheduler) can continue to the next user instead of crashing.
        print(f"  🔒 Gmail auth unavailable for user '{user_id}': {e}")
        return None

    # Construct clean MIME message string
    mime_parts = [
        f"Subject: {subject}",
        "Content-Type: text/plain; charset=utf-8",
        "",
        body
    ]
    if "@" in to:
        mime_parts.insert(0, f"To: {to}")
    mime_message = "\n".join(mime_parts)

    # Base64url encode the MIME payload (remove padding, swap chars)
    raw_bytes = base64.urlsafe_b64encode(mime_message.encode("utf-8"))
    raw_str = raw_bytes.decode("utf-8").replace("=", "")

    draft_payload = {
        "message": {
            "raw": raw_str
        }
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/drafts",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=draft_payload,
                timeout=10.0
            )

        if res.status_code in (200, 201):
            draft_data = res.json()
            print(f"  ✉️  Gmail draft successfully created: {draft_data.get('id')}")
            return draft_data
        else:
            print(f"  ❌ Failed to create Gmail draft: {res.status_code} - {res.text}")
            return None

    except Exception as e:
        print(f"  ❌ Error calling Gmail API: {e}")
        return None
