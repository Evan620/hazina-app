"""
Hazina Backend - FastAPI Application
AI-powered NSE investor intelligence platform
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.api.v1 import sentiment, listing, prospectus, market, predictions
from app.db.database import engine, Base, async_session_maker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    logger.info("Starting Hazina backend...")
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Add snippet column if it doesn't exist (migration)
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text(
                "ALTER TABLE sentiment_signals ADD COLUMN IF NOT EXISTS snippet TEXT"
            ))
            logger.info("Added snippet column to sentiment_signals")
    except Exception as e:
        logger.debug(f"Snippet column migration: {e}")

    # Start prediction cache scheduler
    from app.services.prediction_scheduler import start_scheduler
    start_scheduler()
    logger.info("Prediction cache scheduler started (3x daily updates)")

    # Run initial cache update if empty
    from app.services.prediction_scheduler import get_cached_predictions, update_prediction_cache
    from app.db.database import StockPrediction
    from sqlalchemy import select, func

    async with async_session_maker() as session:
        count = await session.scalar(select(func.count()).select_from(StockPrediction))
        if count == 0:
            logger.info("Cache empty, running initial prediction update...")
            await update_prediction_cache()

    logger.info("Hazina backend ready!")
    yield

    # Shutdown
    logger.info("Shutting down Hazina backend...")
    from app.services.prediction_scheduler import stop_scheduler
    stop_scheduler()


# Create FastAPI app
app = FastAPI(
    title="Hazina API",
    description="AI-powered NSE investor intelligence platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "https://hazina-app-phi.vercel.app",
        "https://hazina-bzlcky88n-lazarus-projects-8a761c11.vercel.app",
        "https://hazina-frontend-production.up.railway.app",
    ],  # Frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(market.router, prefix="/api/v1/market", tags=["Market"])
app.include_router(sentiment.router, prefix="/api/v1/sentiment", tags=["Sentiment"])
app.include_router(listing.router, prefix="/api/v1/listing", tags=["Listing"])
app.include_router(prospectus.router, prefix="/api/v1/prospectus", tags=["Prospectus"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["Predictions"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "hazina-backend",
        "version": "0.1.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Hazina API - AI-powered NSE investor intelligence",
        "docs": "/docs",
        "health": "/health"
    }
