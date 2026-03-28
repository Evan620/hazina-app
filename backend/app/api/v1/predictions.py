"""
Price Prediction API endpoints
Multi-horizon price direction predictions based on sentiment fusion (CACHED VERSION)

Predictions are cached in the database and updated 3x daily.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging
from datetime import datetime

from app.services.prediction_scheduler import get_cached_predictions, update_prediction_cache

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stock/{symbol}")
async def get_stock_predictions(
    symbol: str,
    horizons: str = Query("3,7,14", description="Comma-separated list of horizon days")
):
    """
    Get cached price predictions for a specific stock.

    Args:
        symbol: Stock symbol (e.g., "SCOM")
        horizons: Prediction horizons in days, comma-separated (default: "3,7,14")

    Returns:
        Stock prediction with multi-horizon forecasts from cache
    """
    try:
        all_predictions = await get_cached_predictions()

        # Find the requested stock
        pred = next((p for p in all_predictions if p["symbol"] == symbol.upper()), None)

        if not pred:
            raise HTTPException(status_code=404, detail=f"No cached prediction found for {symbol}")

        # Parse horizons to filter if needed
        horizon_list = [int(h.strip()) for h in horizons.split(",")]
        filtered_predictions = [
            p for p in pred["predictions"]
            if p["horizon_days"] in horizon_list
        ]

        return {
            "symbol": pred["symbol"],
            "current_price": pred["current_price"],
            "predictions": filtered_predictions,
            "sentiment": {
                "overall": pred["overall_sentiment"],
                "news": pred["news_sentiment"],
                **({"twitter": pred["twitter_sentiment"]} if pred.get("twitter_sentiment") is not None else {})
            },
            "signal_count": pred["signal_count"],
            "last_updated": pred.get("updated_at"),
            "source": "Hazina Cached Predictions (updated 3x daily)"
        }

    except Exception as e:
        logger.error(f"Error fetching predictions for {symbol}: {e}")
        # Return demo data on error
        demo = get_demo_predictions(symbol.upper())
        return {
            "symbol": demo.symbol,
            "current_price": demo.current_price,
            "predictions": [
                {
                    "horizon_days": p.horizon_days,
                    "direction": p.direction,
                    "confidence": p.confidence,
                    "reasoning": p.reasoning
                }
                for p in demo.predictions
            ],
            "sentiment": {
                "overall": demo.overall_sentiment,
                "news": demo.news_sentiment,
                "twitter": demo.twitter_sentiment
            },
            "signal_count": demo.signal_count,
            "last_updated": demo.last_updated,
            "source": "Demo data (API unavailable)",
            "error": str(e)
        }


@router.get("/batch")
async def get_batch_predictions(
    symbols: str = Query("", description="Comma-separated list of symbols (empty = all stocks)"),
    horizons: str = Query("3,7,14", description="Comma-separated list of horizon days"),
    page: int = Query(1, description="Page number (1-based)"),
    page_size: int = Query(20, description="Number of stocks per page"),
    sort: str = Query("signal_count", description="Sort by: signal_count, symbol, sentiment")
):
    """
    Get cached predictions for multiple stocks with pagination.

    Args:
        symbols: Comma-separated stock symbols (empty = all stocks)
        horizons: Prediction horizons in days, comma-separated
        page: Page number (1-based)
        page_size: Number of stocks per page (default: 20)
        sort: Sort by field (signal_count, symbol, sentiment)

    Returns:
        Paginated list of stock predictions from cache
    """
    try:
        # Get all cached predictions
        all_predictions = await get_cached_predictions()

        if not all_predictions:
            raise HTTPException(status_code=404, detail="No cached predictions found. Run initial cache update.")

        # Filter by requested symbols if provided
        symbol_list = None
        if symbols and symbols.strip():
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            filtered = [p for p in all_predictions if p["symbol"] in symbol_list]
            if not filtered:
                raise HTTPException(status_code=404, detail=f"No predictions found for symbols: {symbols}")
            all_predictions = filtered

        # Sort predictions
        reverse = sort == "signal_count"  # highest first
        all_predictions.sort(key=lambda x: x.get(sort.replace("_sentiment", "") or "symbol", ""), reverse=reverse)

        # Pagination
        total = len(all_predictions)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        paginated = all_predictions[start_idx:end_idx]

        # Transform to API format
        predictions = []
        for p in paginated:
            pred_data = {
                "symbol": p["symbol"],
                "current_price": p["current_price"],
                "predictions": p["predictions"],
                "overall_sentiment": p["overall_sentiment"],
                "news_sentiment": p.get("news_sentiment", 0.5),
                "signal_count": p["signal_count"]
            }
            # Only include twitter_sentiment if we have data
            if p.get("twitter_sentiment") is not None:
                pred_data["twitter_sentiment"] = p["twitter_sentiment"]
            predictions.append(pred_data)

        # Get the most recent update time
        last_update = max((p.get("updated_at") for p in all_predictions), default=None)

        total_pages = (total + page_size - 1) // page_size

        return {
            "predictions": predictions,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "last_updated": last_update,
            "source": "Hazina Cached Predictions (updated 3x daily)"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in batch predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching predictions: {str(e)}")
        demo_predictions = get_demo_batch_predictions()

        return {
            "predictions": [
                {
                    "symbol": p.symbol,
                    "current_price": p.current_price,
                    "predictions": [
                        {
                            "horizon_days": pred.horizon_days,
                            "direction": pred.direction,
                            "confidence": pred.confidence,
                            "reasoning": pred.reasoning
                        }
                        for pred in p.predictions
                    ],
                    "overall_sentiment": p.overall_sentiment,
                    "signal_count": p.signal_count
                }
                for p in demo_predictions
            ],
            "count": len(demo_predictions),
            "source": "Demo data (API unavailable)",
            "cache_status": "error",
            "error": str(e)
        }


@router.get("/top")
async def get_top_predictions(
    limit: int = Query(5, description="Number of top predictions"),
    horizon: int = Query(7, description="Prediction horizon in days")
):
    """
    Get top bullish/bearish predictions for a specific horizon (from cache).

    Args:
        limit: Number of top stocks to return
        horizon: Prediction horizon in days

    Returns:
        Top bullish and bearish stocks
    """
    try:
        all_predictions = await get_cached_predictions()

        if not all_predictions:
            return {
                "bullish": [],
                "bearish": [],
                "horizon_days": horizon,
                "source": "Demo data (cache empty)",
                "cache_status": "empty"
            }

        # Sort by sentiment for this horizon
        scored = []
        for pred in all_predictions:
            for p in pred["predictions"]:
                if p["horizon_days"] == horizon:
                    direction_score = {"UP": 1, "HOLD": 0, "DOWN": -1}.get(p["direction"], 0)
                    scored.append({
                        "symbol": pred["symbol"],
                        "direction": p["direction"],
                        "confidence": p["confidence"],
                        "overall_sentiment": pred["overall_sentiment"],
                        "current_price": pred["current_price"],
                        "reasoning": p["reasoning"],
                        "sort_score": direction_score * p["confidence"]
                    })
                    break

        # Sort by score
        scored.sort(key=lambda x: x["sort_score"], reverse=True)

        # Split bullish and bearish
        bullish = [s for s in scored if s["direction"] == "UP"][:limit]
        bearish = [s for s in scored if s["direction"] == "DOWN"][:limit]

        return {
            "bullish": [
                {
                    "symbol": b["symbol"],
                    "current_price": b["current_price"],
                    "confidence": b["confidence"],
                    "sentiment": b["overall_sentiment"],
                    "reasoning": b["reasoning"]
                }
                for b in bullish
            ],
            "bearish": [
                {
                    "symbol": b["symbol"],
                    "current_price": b["current_price"],
                    "confidence": b["confidence"],
                    "sentiment": b["overall_sentiment"],
                    "reasoning": b["reasoning"]
                }
                for b in bearish
            ],
            "horizon_days": horizon,
            "source": "Hazina Cached Predictions"
        }

    except Exception as e:
        logger.error(f"Error getting top predictions: {e}")
        return {
            "bullish": [],
            "bearish": [],
            "horizon_days": horizon,
            "error": str(e)
        }


@router.post("/refresh")
async def refresh_predictions():
    """
    Manually trigger a prediction cache update.
    Use this to immediately refresh predictions instead of waiting for the scheduled update.
    """
    try:
        await update_prediction_cache()

        return {
            "status": "success",
            "message": "Prediction cache updated successfully",
            "updated_at": datetime.utcnow().isoformat(),
            "count": len(await get_cached_predictions())
        }
    except Exception as e:
        logger.error(f"Error refreshing predictions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to refresh: {str(e)}")


@router.get("/health")
async def prediction_health():
    """Health check for prediction engine."""
    cached = await get_cached_predictions()

    return {
        "status": "operational",
        "model": "Sentiment Fusion v1.0 (Cached)",
        "cache_size": len(cached),
        "update_schedule": "3x daily (06:00, 14:00, 22:00 UTC)",
        "sources": ["News (Business Daily, The Star)", "Twitter/X API"],
        "weights": {"news": 0.70, "twitter": 0.30},
        "horizons": [3, 7, 14],
        "currency": "KES"
    }
