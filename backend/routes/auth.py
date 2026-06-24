"""
LIFEOS — Google OAuth Authentication Routes
"""
import time
import json
import httpx

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


@router.get("/auth/login")
async def login(request: Request):
    """Redirect user to Google OAuth consent page."""
    client_id = settings.GOOGLE_CLIENT_ID
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    scope = "openid email profile"

    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scope.replace(' ', '%20')}"
        f"&access_type=offline"
        f"&prompt=select_account"
    )
    return RedirectResponse(google_auth_url)


@router.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback, create session, redirect to dashboard."""
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    if error or not code:
        return RedirectResponse("/login.html?error=access_denied")

    try:
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

        # Upsert user in MongoDB
        try:
            from db.mongodb import get_db
            db = get_db()
            users_col = db["users"]
            
            set_dict = {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "google_id": user_info.get("sub"),
                "last_login": time.time(),
            }
            if picture_base64:
                set_dict["picture_base64"] = picture_base64
                
            await users_col.update_one(
                {"google_id": user_info.get("sub")},
                {"$set": set_dict, "$setOnInsert": {
                    "created_at": time.time(),
                    "streak_days": 0,
                    "productivity_score": 0,
                }},
                upsert=True,
            )
        except Exception as db_err:
            print(f"  ⚠️  Could not save user to DB: {db_err}")

        # Create session cookie
        session_token = _make_session_token(user_info)
        response = RedirectResponse("/dashboard.html")
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
            return JSONResponse({"user": {
                "name": user.get("name") or payload.get("name"),
                "email": user.get("email") or payload.get("email"),
                "picture": picture,
            }})
    except Exception as e:
        print(f"  ⚠️  Error retrieving user from DB in /auth/me: {e}")

    return JSONResponse({"user": {
        "name": payload.get("name"),
        "email": payload.get("email"),
        "picture": payload.get("picture"),
    }})
