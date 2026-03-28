"""
Prediction Cache Scheduler
Updates cached predictions 3 times daily (every 8 hours)

Schedule: 6:00 AM, 2:00 PM, 10:00 PM EAT
"""

import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.database import async_session_maker, StockPrediction
from app.services.prediction_engine import generate_batch_predictions
from app.services.sentiment_fusion import NSE_SYMBOLS

logger = logging.getLogger(__name__)

# Use ALL NSE symbols (50+ stocks)
ALL_NSE_SYMBOLS = list(NSE_SYMBOLS.keys())

# Scheduler instance
scheduler = AsyncIOScheduler()


async def update_prediction_cache():
    """
    Generate and cache predictions for all major NSE stocks.
    Called by scheduler 3x daily.
    """
    logger.info(f"[{datetime.utcnow()}] Starting prediction cache update...")

    try:
        # Generate predictions
        predictions = await generate_batch_predictions(ALL_NSE_SYMBOLS)

        if not predictions:
            logger.error("No predictions generated - cache update failed")
            return

        # Save to database
        async with async_session_maker() as session:
            for pred in predictions:
                # Check if prediction exists
                from sqlalchemy import select
                result = await session.execute(
                    select(StockPrediction).where(StockPrediction.symbol == pred.symbol)
                )
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing
                    existing.current_price = pred.current_price
                    existing.overall_sentiment = pred.overall_sentiment
                    existing.news_sentiment = pred.news_sentiment
                    existing.twitter_sentiment = pred.twitter_sentiment
                    existing.has_twitter = pred.has_twitter
                    existing.signal_count = pred.signal_count
                    existing.predictions = {
                        "predictions": [
                            {
                                "horizon_days": p.horizon_days,
                                "direction": p.direction,
                                "confidence": p.confidence,
                                "reasoning": p.reasoning
                            }
                            for p in pred.predictions
                        ]
                    }
                    existing.updated_at = datetime.utcnow()
                else:
                    # Create new
                    new_pred = StockPrediction(
                        symbol=pred.symbol,
                        current_price=pred.current_price,
                        overall_sentiment=pred.overall_sentiment,
                        news_sentiment=pred.news_sentiment,
                        twitter_sentiment=pred.twitter_sentiment,
                        has_twitter=pred.has_twitter,
                        signal_count=pred.signal_count,
                        predictions={
                            "predictions": [
                                {
                                    "horizon_days": p.horizon_days,
                                    "direction": p.direction,
                                    "confidence": p.confidence,
                                    "reasoning": p.reasoning
                                }
                                for p in pred.predictions
                            ]
                        }
                    )
                    session.add(new_pred)

            await session.commit()

        logger.info(f"✅ Cached {len(predictions)} stock predictions")

    except Exception as e:
        logger.error(f"❌ Error updating prediction cache: {e}")


async def get_cached_predictions() -> list:
    """
    Fetch all cached predictions from database.

    Returns:
        List of prediction dicts matching the API format
    """
    async with async_session_maker() as session:
        from sqlalchemy import select

        result = await session.execute(
            select(StockPrediction).order_by(StockPrediction.symbol)
        )
        cached = result.scalars().all()

        if not cached:
            return []

        # Transform to API format
        predictions = []
        for c in cached:
            pred_data = c.predictions or {}
            pred_list = pred_data.get("predictions", [])

            predictions.append({
                "symbol": c.symbol,
                "current_price": c.current_price,
                "overall_sentiment": c.overall_sentiment,
                "news_sentiment": c.news_sentiment,
                "twitter_sentiment": c.twitter_sentiment,
                "has_twitter": c.has_twitter,
                "signal_count": c.signal_count,
                "predictions": pred_list,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            })

        return predictions


def start_scheduler():
    """
    Start the prediction cache scheduler.
    Runs 3 times daily at 6:00 AM, 2:00 PM, 10:00 PM EAT.
    """
    # Schedule: 6 AM, 2 PM, 10 PM (every 8 hours)
    scheduler.add_job(
        update_prediction_cache,
        'cron',
        hour='6,14,22',  # UTC times (adjust for EAT if needed)
        minute='0',
        id='prediction_cache_update',
        replace_existing=True
    )

    scheduler.start()
    logger.info("🗓️ Prediction cache scheduler started (runs 3x daily at 06:00, 14:00, 22:00 UTC)")


def stop_scheduler():
    """Stop the scheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Prediction cache scheduler stopped")


if __name__ == "__main__":
    # Manual trigger for testing
    import sys
    logging.basicConfig(level=logging.INFO)

    async def main():
        if len(sys.argv) > 1 and sys.argv[1] == "--run":
            await update_prediction_cache()
        else:
            start_scheduler()
            try:
                # Keep running
                while True:
                    await asyncio.sleep(3600)
            except KeyboardInterrupt:
                stop_scheduler()

    asyncio.run(main())
