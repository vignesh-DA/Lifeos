"""
LIFEOS — FastAPI Application Entry Point
Your Personal Life Operating System 🚀
"""
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

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
        print("  ℹ️  Running without database — some features disabled")

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

# ─── Mount Frontend Static Files ───
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# ─── Import and Include Routers ───
from routes.tasks import router as tasks_router
from routes.agent import router as agent_router
from routes.crisis import router as crisis_router
from routes.insights import router as insights_router

app.include_router(tasks_router, prefix="/api", tags=["Tasks"])
app.include_router(agent_router, prefix="/api", tags=["Agent"])
app.include_router(crisis_router, prefix="/api", tags=["Crisis"])
app.include_router(insights_router, prefix="/api", tags=["Insights"])


# ─── Health Check ───
@app.get("/health", tags=["System"])
async def health():
    """Health check endpoint."""
    return {
        "status": "LIFEOS is alive 🚀",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint — redirect info."""
    return {
        "message": "Welcome to LIFEOS API",
        "docs": "/docs",
        "health": "/health",
    }
