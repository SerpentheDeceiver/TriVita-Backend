import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.graph.health_graph import build_graph
from app.routes.profile import router as profile_router
from app.routes.daily_logs import router as daily_logs_router
from app.routes.meal_plan import router as meal_plan_router
from app.routes.analytics import router as analytics_router
from app.routes.chatbot import router as chatbot_router
from app.routes.sleep_insights import router as sleep_insights_router
from app.routes.hydration_insights import router as hydration_insights_router
from app.routes.predictive import router as predictive_router
from app.routes.notifications import router as notifications_router
from app.scheduler import create_scheduler, seed_daily_states

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Application lifespan  (startup / shutdown)
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("Starting notification scheduler…")
    _scheduler = create_scheduler()
    _scheduler.start()

    # Seed today's notification states for all users with FCM tokens
    try:
        seeded = await seed_daily_states()
        logger.info("Startup seed: %d notification slots created for today.", seeded)
    except Exception as exc:
        logger.warning("Startup seed failed (non-fatal): %s", exc)

    yield   # application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down notification scheduler…")
    _scheduler.shutdown(wait=False)


app = FastAPI(
    title="Health AI Multi-Agent System",
    description="AI-powered health analysis with multi-agent system",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(profile_router, prefix="/profile")
app.include_router(daily_logs_router, prefix="/log")
app.include_router(meal_plan_router)
app.include_router(analytics_router)
app.include_router(chatbot_router)
app.include_router(sleep_insights_router)
app.include_router(hydration_insights_router)
app.include_router(predictive_router)
app.include_router(notifications_router, prefix="/notifications")

graph = build_graph()


@app.get("/")
def root():
    """API information."""
    return {
        "app": "Health AI Multi-Agent System",
        "version": "2.0.0",
        "status": "active",
        "endpoints": {
            "/analyze": "POST - Analyze health data with multi-agent system"
        }
    }


@app.get("/health")
def health_check():
    """Lightweight ping used by the Flutter app to auto-detect the backend URL."""
    return {"status": "ok"}


@app.post("/analyze")
def analyze(data: dict):
    """
    Analyze health data using the multi-agent system.
    
    Expected input format:
    {
        "profile": {
            "age": 28,
            "weight": 72,
            "height": 175,
            "gender": "male",
            "weight_goal": "maintain",
            "activity_level": "moderate"
        },
        "sleep_log": {
            "sleep_hours": 7.5,
            "bed_time": "23:00",
            "wake_time": "06:30",
            "sleep_quality": "good"
        },
        "hydration_log": {
            "water_intake_ml": 2200,
            "caffeine_intake_mg": 150,
            "urine_color": "light_yellow"
        },
        "nutrition_log": {
            "total_calories": 2050,
            "total_protein_g": 140,
            "total_carbs_g": 210,
            "total_fat_g": 65,
            "meal_count": 4
        }
    }
    """
    result = graph.invoke(data)
    return result
