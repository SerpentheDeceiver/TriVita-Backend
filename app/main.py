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


# Startup and shutdown logic
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting notification scheduler...")
    _scheduler = create_scheduler()
    _scheduler.start()

    # Seed notification states for today
    try:
        seeded = await seed_daily_states()
        logger.info("Startup seed: %d slots created.", seeded)
    except Exception as exc:
        logger.warning("Startup seed failed: %s", exc)

    yield

    logger.info("Shutting down scheduler...")
    _scheduler.shutdown(wait=False)

app = FastAPI(
    title="Health AI Backend",
    description="Backend for TriVita Health App",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
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
    return {"app": "TriVita Health AI", "status": "active"}

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/analyze")
def analyze(data: dict):
    # Analyze data using the graph
    result = graph.invoke(data)
    return result
