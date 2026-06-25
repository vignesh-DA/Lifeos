"""
LIFEOS — Google APIs Integration Helper
Uses raw httpx calls to interface with Google Calendar & Gmail APIs with auto-refreshing OAuth tokens.
"""
import time
import base64
import httpx
from config import settings
from db.mongodb import get_db


async def get_google_access_token(user_id: str, required_scope: str) -> str | None:
    """
    Load user from DB, check if token is valid for required_scope,
    refresh if expired, and return a valid access token.
    """
    db = get_db()
    user = await db["users"].find_one({"google_id": user_id})
    if not user or "google_tokens" not in user:
        print(f"  ❌ No google_tokens found for user: {user_id}")
        return None

    tokens = user["google_tokens"]
    scopes = tokens.get("scopes", [])
    
    # Check if authorized for required scope
    if required_scope not in scopes:
        print(f"  ❌ Required scope '{required_scope}' not authorized for user: {user_id}")
        return None

    access_token = tokens.get("access_token")
    expires_at = tokens.get("expires_at", 0)
    refresh_token = tokens.get("refresh_token")

    # If token is still valid (with 60 second margin), return it
    if access_token and expires_at > time.time() + 60:
        return access_token

    # Token is expired, try to refresh it
    if not refresh_token:
        print(f"  ❌ Access token expired and no refresh_token available for user: {user_id}")
        return None

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
                print(f"  ❌ Google token refresh failed: {data}")
                return None

            new_access_token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            new_expires_at = int(time.time()) + expires_in

            # Update DB with new token
            tokens["access_token"] = new_access_token
            tokens["expires_at"] = new_expires_at
            
            await db["users"].update_one(
                {"google_id": user_id},
                {"$set": {"google_tokens": tokens}}
            )
            print(f"  ✅ Access token successfully refreshed.")
            return new_access_token

    except Exception as e:
        print(f"  ❌ Error refreshing Google access token: {e}")
        return None


async def create_calendar_event(user_id: str, task: dict) -> dict | None:
    """
    Create a scheduled event on Google Calendar for a task.
    Includes custom priority-based reminders.
    """
    scope = "https://www.googleapis.com/auth/calendar.events"
    token = await get_google_access_token(user_id, scope)
    if not token:
        return None

    title = task.get("title", "LIFEOS Focus Session")
    description = task.get("description", "")
    priority = task.get("priority_score", 5.0)

    # Determine timing
    # Default to scheduling it starting in 1 hour if no deadline/schedule is set
    from datetime import datetime, timezone, timedelta
    
    start_time = None
    if task.get("deadline"):
        try:
            # Parse deadline ISO string
            dl_dt = datetime.fromisoformat(task.get("deadline").replace("Z", "+00:00"))
            # Schedule the task study block 4 hours before the deadline (or today if it's too close)
            target_start = dl_dt - timedelta(hours=4)
            now = datetime.now(timezone.utc)
            if target_start < now:
                target_start = now + timedelta(minutes=30)
            start_time = target_start
        except Exception:
            start_time = datetime.now(timezone.utc) + timedelta(hours=1)
    else:
        start_time = datetime.now(timezone.utc) + timedelta(hours=1)

    duration_hours = task.get("estimated_hours", 1.0)
    end_time = start_time + timedelta(hours=duration_hours)

    start_str = start_time.isoformat()
    end_str = end_time.isoformat()

    # Define reminders dynamically based on priority
    # Green/Low (<5.0), Orange/Medium (5.0-8.0), Red/Urgent (8.0+)
    reminders = {"useDefault": False, "overrides": []}
    if priority >= 8.0:
        reminders["overrides"] = [
            {"method": "popup", "minutes": 120},  # 2 hours before
            {"method": "popup", "minutes": 30},   # 30 minutes before
            {"method": "email", "minutes": 15},   # 15 minutes before
        ]
        color_id = "11"  # Red/Tomato
    elif priority >= 5.0:
        reminders["overrides"] = [
            {"method": "popup", "minutes": 60},   # 1 hour before
            {"method": "popup", "minutes": 15},   # 15 minutes before
        ]
        color_id = "5"   # Yellow/Banana
    else:
        reminders["overrides"] = [
            {"method": "popup", "minutes": 15},   # 15 minutes before
        ]
        color_id = "2"   # Green/Sage

    event_payload = {
      "summary": f"🎯 LIFEOS: {title}",
      "description": f"Focus Block generated by LIFEOS.\n\nDescription: {description}\nPriority Score: {priority}/10",
      "start": { "dateTime": start_str, "timeZone": "UTC" },
      "end": { "dateTime": end_str, "timeZone": "UTC" },
      "colorId": color_id,
      "reminders": reminders
    }

    try:
        # Check if they already have an event for this task, delete it first to prevent duplicates
        existing_event_id = task.get("google_calendar_event_id")
        async with httpx.AsyncClient() as client:
            if existing_event_id:
                try:
                    await client.delete(
                        f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{existing_event_id}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=5.0
                    )
                except Exception:
                    pass

            # Create event
            res = await client.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json=event_payload,
                timeout=10.0
            )
            
            if res.status_code in [200, 201]:
                event_data = res.json()
                print(f"  📅 Calendar event successfully created: {event_data.get('id')}")
                return event_data
            else:
                print(f"  ❌ Failed to create calendar event: {res.status_code} - {res.text}")
                return None

    except Exception as e:
        print(f"  ❌ Error calling Google Calendar API: {e}")
        return None


async def create_gmail_draft(user_id: str, to: str, subject: str, body: str) -> dict | None:
    """
    Create a compose draft in user's Gmail drafts folder.
    """
    scope = "https://www.googleapis.com/auth/gmail.compose"
    token = await get_google_access_token(user_id, scope)
    if not token:
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

            if res.status_code in [200, 201]:
                draft_data = res.json()
                print(f"  ✉️  Gmail draft successfully created: {draft_data.get('id')}")
                return draft_data
            else:
                print(f"  ❌ Failed to create Gmail draft: {res.status_code} - {res.text}")
                return None

    except Exception as e:
        print(f"  ❌ Error calling Gmail API: {e}")
        return None
