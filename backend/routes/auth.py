"""
LIFEOS — Google OAuth Authentication Routes
"""
import time
import json
import httpx

from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse

from config import settings

router = APIRouter(tags=["Auth"])


def _make_session_token(user_info: dict) -> str:
    """Create a simple signed session token (base64 JSON + HMAC)."""
    import base64, hmac, hashlib
    payload = json.dumps({
        "email": user_info.get("email", ""),
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
        "google_id": user_info.get("sub", ""),
        "exp": int(time.time()) + 86400,
    })
    b64 = base64.b64encode(payload.encode()).decode()
    sig = hmac.new(
        settings.SECRET_KEY.encode(),
        b64.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{b64}.{sig}"


def _verify_session_token(token: str) -> dict | None:
    """Verify and decode a session token. Returns payload or None."""
    import base64, hmac, hashlib
    try:
        b64, sig = token.rsplit(".", 1)
        expected = hmac.new(
            settings.SECRET_KEY.encode(),
            b64.encode(),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.b64decode(b64).decode())
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None


@router.get("/auth/mock")
async def mock_login(request: Request):
    """Log in with a mock user for development testing and validation."""
    user_info = {
        "email": "mockuser@example.com",
        "name": "Alex Mercer",
        "picture": "https://ui-avatars.com/api/?name=Alex+Mercer&background=7C5CFF&color=fff",
        "sub": "mock_google_id_12345",
    }
    session_token = _make_session_token(user_info)
    
    try:
        from db.mongodb import get_db
        db = get_db()
        users_col = db["users"]
        await users_col.update_one(
            {"google_id": "mock_google_id_12345"},
            {"$set": {
                "email": "mockuser@example.com",
                "name": "Alex Mercer",
                "google_id": "mock_google_id_12345",
                "last_login": time.time(),
                "picture": "https://ui-avatars.com/api/?name=Alex+Mercer&background=7C5CFF&color=fff",
                "google_tokens": {
                    "access_token": "mock_access_token",
                    "expires_at": time.time() + 3600,
                    "scopes": [
                        "openid", "email", "profile",
                        "https://www.googleapis.com/auth/calendar.events",
                        "https://www.googleapis.com/auth/gmail.compose"
                    ],
                }
            }, "$setOnInsert": {
                "created_at": time.time(),
                "streak_days": 5,
                "best_streak": 12,
                "productivity_score": 82.0,
            }},
            upsert=True,
        )
    except Exception as db_err:
        print(f"Mock login DB update failed: {db_err}")

    response = RedirectResponse("/dashboard.html")
    response.set_cookie(
        "lifeos_session",
        session_token,
        httponly=True,
        max_age=86400,
        samesite="lax",
    )
    return response


@router.get("/auth/login")
async def login(request: Request, scope: Optional[str] = None, redirect_url: Optional[str] = None):
    """Redirect user to Google OAuth consent page."""
    client_id = settings.GOOGLE_CLIENT_ID
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    
    # Scopes
    scopes = ["openid", "email", "profile"]
    extra_params = ""
    if scope == "calendar":
        scopes.append("https://www.googleapis.com/auth/calendar.events")
        extra_params = "&prompt=consent&include_granted_scopes=true"
    elif scope == "gmail":
        scopes.append("https://www.googleapis.com/auth/gmail.compose")
        extra_params = "&prompt=consent&include_granted_scopes=true"
    import urllib.parse
    
    query_params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
        "access_type": "offline",
    }
    
    if scope in ["calendar", "gmail"]:
        query_params["prompt"] = "consent"
        query_params["include_granted_scopes"] = "true"
    else:
        query_params["prompt"] = "select_account"

    if redirect_url:
        query_params["state"] = redirect_url

    query_string = urllib.parse.urlencode(query_params)
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"
    
    return RedirectResponse(google_auth_url)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback, create session, redirect to dashboard."""
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    if error or not code:
        return RedirectResponse("/login.html?error=access_denied")

    try:
        # Check if user is already logged in
        existing_user_payload = None
        session_cookie = request.cookies.get("lifeos_session")
        if session_cookie:
            existing_user_payload = _verify_session_token(session_cookie)

        # Exchange code for tokens
        async with httpx.AsyncClient() as client:
            token_res = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )
            token_data = token_res.json()

            if "error" in token_data:
                print(f"Google OAuth token exchange failed: {token_data}")
                return RedirectResponse("/login.html?error=token_failed")

            # Fetch user info
            userinfo_res = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            user_info = userinfo_res.json()

            # Download and base64-encode user profile picture to store it in DB
            picture_url = user_info.get("picture")
            picture_base64 = ""
            if picture_url:
                try:
                    img_res = await client.get(picture_url, timeout=5.0)
                    if img_res.status_code == 200:
                        import base64
                        content_type = img_res.headers.get("content-type", "image/jpeg")
                        encoded = base64.b64encode(img_res.content).decode("utf-8")
                        picture_base64 = f"data:{content_type};base64,{encoded}"
                        print("  ✅ Downloaded and base64-encoded user avatar")
                except Exception as img_err:
                    print(f"  ⚠️  Failed to download user avatar: {img_err}")

            # Fetch exact scopes from tokeninfo to be 100% accurate
            tokeninfo_res = await client.get(f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token_data['access_token']}")
            tokeninfo_data = tokeninfo_res.json()
            granted_scopes = tokeninfo_data.get("scope", "").split(" ")
            
        expires_in = token_data.get("expires_in", 3600)
        expires_at = int(time.time()) + expires_in

        google_tokens = {
            "access_token": token_data.get("access_token"),
            "expires_at": expires_at,
            "scopes": granted_scopes,
        }
        if token_data.get("refresh_token"):
            google_tokens["refresh_token"] = token_data.get("refresh_token")

        # Determine google_id
        google_id = user_info.get("sub") or (existing_user_payload.get("google_id") if existing_user_payload else None)
        if not google_id:
            return RedirectResponse("/login.html?error=server_error")

        # Upsert user in MongoDB
        try:
            from db.mongodb import get_db
            db = get_db()
            users_col = db["users"]
            
            # Find existing user first to merge google_tokens
            existing_user = await users_col.find_one({"google_id": google_id})
            
            # Keep old refresh_token if new one is missing
            if existing_user and "google_tokens" in existing_user:
                old_tokens = existing_user["google_tokens"]
                if "refresh_token" not in google_tokens and "refresh_token" in old_tokens:
                    google_tokens["refresh_token"] = old_tokens["refresh_token"]
                # We no longer merge scopes here. The new token's exact scopes (via tokeninfo) are what's valid.

            set_dict = {
                "email": user_info.get("email") or (existing_user.get("email") if existing_user else ""),
                "name": user_info.get("name") or (existing_user.get("name") if existing_user else ""),
                "google_id": google_id,
                "last_login": time.time(),
                "google_tokens": google_tokens,
            }
            if picture_base64:
                set_dict["picture_base64"] = picture_base64
            elif picture_url:
                set_dict["picture"] = picture_url

            await users_col.update_one(
                {"google_id": google_id},
                {"$set": set_dict, "$setOnInsert": {
                    "created_at": time.time(),
                    "streak_days": 0,
                    "productivity_score": 0,
                }},
                upsert=True,
            )
        except Exception as db_err:
            print(f"  ⚠️  Could not save user to DB in callback: {db_err}")

        # Create session cookie
        session_token = _make_session_token(user_info)
        
        # Determine redirect target
        state = request.query_params.get("state")
        target_url = state if state and state.startswith("/") else "/dashboard.html"
        
        response = RedirectResponse(target_url)
        response.set_cookie(
            "lifeos_session",
            session_token,
            httponly=True,
            max_age=86400,
            samesite="lax",
        )
        return response

    except Exception as e:
        print(f"OAuth callback error: {e}")
        return RedirectResponse("/login.html?error=server_error")


@router.get("/auth/logout")
async def logout():
    """Clear session and redirect to login."""
    response = RedirectResponse("/login.html")
    response.delete_cookie("lifeos_session")
    return response


@router.get("/auth/me")
async def get_current_user(request: Request):
    """Return current user info from session cookie, loading base64 avatar from DB if available."""
    token = request.cookies.get("lifeos_session")
    if not token:
        return JSONResponse({"user": None})
    payload = _verify_session_token(token)
    if not payload:
        return JSONResponse({"user": None})
        
    try:
        from db.mongodb import get_db
        db = get_db()
        user = await db["users"].find_one({"google_id": payload.get("google_id")})
        if user:
            picture = user.get("picture_base64") or user.get("picture") or payload.get("picture")
            
            # Check calendar and gmail connection status based on granted scopes
            scopes = user.get("google_tokens", {}).get("scopes", [])
            calendar_connected = "https://www.googleapis.com/auth/calendar.events" in scopes
            gmail_connected = "https://www.googleapis.com/auth/gmail.compose" in scopes
            
            return JSONResponse({"user": {
                "name": user.get("name") or payload.get("name"),
                "email": user.get("email") or payload.get("email"),
                "picture": picture,
                "calendar_connected": calendar_connected,
                "gmail_connected": gmail_connected,
                "google_id": payload.get("google_id"),
            }})
    except Exception as e:
        print(f"  ⚠️  Error retrieving user from DB in /auth/me: {e}")

    return JSONResponse({"user": {
        "name": payload.get("name"),
        "email": payload.get("email"),
        "picture": payload.get("picture"),
        "calendar_connected": False,
        "gmail_connected": False,
        "google_id": payload.get("google_id"),
    }})
