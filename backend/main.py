"""
LIFEOS — FastAPI Application Entry Point
Your Personal Life Operating System 🚀
"""
import sys
import os

# Reconfigure stdout/stderr to use UTF-8 to prevent UnicodeEncodeError on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from db.mongodb import connect_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown events."""
    # ─── STARTUP ───
    print("=" * 50)
    print("🚀 LIFEOS Starting Up...")
    print("=" * 50)

    # Validate configuration
    warnings = settings.validate()
    for w in warnings:
        print(f"  ⚠️  {w}")

    # Connect to MongoDB
    try:
        await connect_db()
    except Exception as e:
        print(f"  ❌ MongoDB connection failed: {e}")
        print("  ℹ️  Falling back to in-memory store...")
        from db.mongodb import use_memory_fallback
        await use_memory_fallback()

    # Load ML models
    try:
        from ml.priority import load_priority_model
        load_priority_model()
        print("  ✅ ML Priority Model loaded")
    except Exception as e:
        print(f"  ⚠️  ML model not loaded: {e}")

    # Download spaCy model if needed
    try:
        import spacy
        try:
            spacy.load("en_core_web_sm")
            print("  ✅ spaCy model ready")
        except OSError:
            print("  📥 Downloading spaCy model...")
            os.system("python -m spacy download en_core_web_sm")
            print("  ✅ spaCy model downloaded")
    except ImportError:
        print("  ⚠️  spaCy not installed")

    print("=" * 50)
    print("🟢 LIFEOS is alive and ready!")
    print("=" * 50)

    yield

    # ─── SHUTDOWN ───
    await close_db()
    print("🔴 LIFEOS shut down")


# ─── Create FastAPI App ───
app = FastAPI(
    title="LIFEOS API",
    description="Your Personal Life Operating System — The Last-Minute Life Saver",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS Middleware ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Session Middleware (for OAuth) ───
from starlette.middleware.sessions import SessionMiddleware
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# ─── Frontend path ───
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

# ─── Import and Include Routers ───
from routes.tasks import router as tasks_router
from routes.agent import router as agent_router
from routes.crisis import router as crisis_router
from routes.insights import router as insights_router
from routes.auth import router as auth_router

app.include_router(tasks_router, prefix="/api", tags=["Tasks"])
app.include_router(agent_router, prefix="/api", tags=["Agent"])
app.include_router(crisis_router, prefix="/api", tags=["Crisis"])
app.include_router(insights_router, prefix="/api", tags=["Insights"])
app.include_router(auth_router, tags=["Auth"])


# ─── Health Check ───
@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint."""
    return {
        "status": "LIFEOS is alive 🚀",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["System"], response_class=HTMLResponse)
async def root():
    """Serve the frontend homepage."""
    index_file = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file, media_type="text/html")
    return HTMLResponse("<h1>LIFEOS — Frontend not found</h1>", status_code=404)


@app.get("/{filename:path}", tags=["System"])
async def serve_frontend(filename: str):
    """Serve frontend files (HTML, CSS, JS, etc.) from the root URL."""
    file_path = os.path.join(frontend_path, filename)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    # Fallback to index.html for SPA-style routing
    return FileResponse(os.path.join(frontend_path, "index.html"), media_type="text/html")
