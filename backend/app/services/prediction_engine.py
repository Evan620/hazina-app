"""
Price Prediction Engine
Generates multi-horizon price direction predictions based on sentiment fusion.

Uses historical sentiment vs price movement correlation to predict
future price direction (UP/DOWN/HOLD) at 3, 7, and 14 day horizons.
"""

import os
import anthropic
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from app.db.database import async_session_maker, SentimentSignal, MarketData


# ============================================================================
# CONFIGURATION
# ============================================================================

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Prediction weights
NEWS_WEIGHT = 0.70
TWITTER_WEIGHT = 0.30

# Sentiment thresholds
BULLISH_THRESHOLD = 0.65
BEARISH_THRESHOLD = 0.40

# Confidence multipliers
HIGH_SENTIMENT_BONUS = 1.15
LOW_SENTIMENT_PENALTY = 0.85


class Direction(Enum):
    UP = "UP"
    DOWN = "DOWN"
    HOLD = "HOLD"


@dataclass
class Prediction:
    """Single prediction for a specific horizon."""
    horizon_days: int
    direction: str
    confidence: float
    reasoning: str


@dataclass
class StockPrediction:
    """Complete prediction set for a stock."""
    symbol: str
    current_price: float
    predictions: List[Prediction]
    overall_sentiment: float
    news_sentiment: float
    twitter_sentiment: float
    signal_count: int
    last_updated: str


# ============================================================================
# PREDICTION LOGIC
# ============================================================================

def sentiment_to_direction(sentiment_score: float) -> str:
    """Convert sentiment score to direction."""
    if sentiment_score >= BULLISH_THRESHOLD:
        return Direction.UP.value
    elif sentiment_score <= BEARISH_THRESHOLD:
        return Direction.DOWN.value
    else:
        return Direction.HOLD.value


def calculate_base_confidence(sentiment_score: float, signal_count: int) -> float:
    """
    Calculate base confidence from sentiment and signal count.

    Higher sentiment strength and more signals = higher confidence.
    """
    # Sentiment strength component (0-50%)
    if sentiment_score >= 0.75:
        sentiment_strength = 0.50
    elif sentiment_score >= 0.65:
        sentiment_strength = 0.40
    elif sentiment_score <= 0.30:
        sentiment_strength = 0.40
    elif sentiment_score <= 0.40:
        sentiment_strength = 0.30
    else:
        sentiment_strength = 0.15  # Neutral zone

    # Signal count component (0-50%, caps at 20+ signals)
    signal_bonus = min(signal_count / 40, 0.50)

    return min(sentiment_strength + signal_bonus, 0.95)


def adjust_confidence_for_horizon(base_confidence: float, horizon_days: int) -> float:
    """
    Adjust confidence based on prediction horizon.

    Shorter horizons = higher confidence (sentiment more reliable)
    Longer horizons = lower confidence (more uncertainty)
    """
    decay_factors = {
        3: 1.0,      # No decay
        7: 0.88,     # 12% reduction
        14: 0.75,    # 25% reduction
    }

    factor = decay_factors.get(horizon_days, 0.75)
    return base_confidence * factor


async def get_historical_accuracy(symbol: str, horizon_days: int) -> float:
    """
    Calculate historical accuracy of sentiment predictions for this symbol.

    In production, this would compare past sentiment vs actual price movement.
    For prototype, returns a default value.
    """
    # TODO: Implement historical accuracy calculation
    # This would:
    # 1. Get sentiment from N days ago
    # 2. Get price N days ago vs current price
    # 3. Check if predicted direction matched actual direction

    # Default values by sector (placeholder)
    return {
        "SCOM": 0.72, "EQTY": 0.68, "KCB": 0.70, "ABSA": 0.65,
        "EABL": 0.71, "COOP": 0.67, "NMG": 0.64, "JUBH": 0.66,
    }.get(symbol, 0.68)


# ============================================================================
# CLAUDE-POWERED REASONING
# ============================================================================

async def generate_prediction_reasoning(
    symbol: str,
    sentiment_data: Dict,
    horizon_days: int,
    direction: str,
    current_price: float
) -> str:
    """
    Use Claude to generate contextual reasoning for the prediction.
    """
    sentiment = sentiment_data.get("overall", 0.5)
    news_score = sentiment_data.get("news", 0.5)
    twitter_score = sentiment_data.get("twitter", 0.5)
    signal_count = sentiment_data.get("signal_count", 0)
    top_signals = sentiment_data.get("top_signals", [])

    direction_desc = {
        "UP": "expected to rise",
        "DOWN": "expected to decline",
        "HOLD": "expected to remain stable"
    }.get(direction, "uncertain")

    # Build context from top signals
    signal_context = ""
    if top_signals:
        for i, sig in enumerate(top_signals[:2], 1):
            snippet = sig.get("snippet", "")[:100]
            reason = sig.get("reason", "")
            signal_context += f"\n  {i}. {sig['sentiment'].upper()} ({sig['confidence']:.0%}): {reason}"
            if snippet:
                signal_context += f"\n     \"{snippet}\""

    prompt = f"""Generate a 1-sentence reasoning for this stock prediction.

Symbol: {symbol}
Prediction: {direction_desc} in {horizon_days} days
Overall Sentiment: {sentiment:.0%} ({"Bullish" if sentiment > 0.5 else "Bearish"})
Signal Count: {signal_count}
Key signals:{signal_context}

Task: Explain WHY this prediction makes sense in 1 concise sentence.
Reference the actual news/sentiment factors above.

Return ONLY the reasoning sentence, nothing else."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    except Exception as e:
        # Better fallback using actual signal data
        if top_signals:
            sig = top_signals[0]
            return f"{sig['sentiment'].capitalize()} sentiment ({sig['confidence']:.0%}): {sig['reason']}"
        elif direction == "UP":
            return f"Positive sentiment ({sentiment:.0%}) from {signal_count} signals suggests upside potential."
        elif direction == "DOWN":
            return f"Negative sentiment ({sentiment:.0%}) from {signal_count} signals indicates downside risk."
        else:
            return f"Mixed signals ({signal_count} mentions) suggest sideways movement."


# ============================================================================
# MAIN PREDICTION ENGINE
# ============================================================================

async def aggregate_sentiment(symbol: str, hours: int = 48) -> Dict:
    """
    Aggregate sentiment from news and Twitter sources.

    Returns:
        {
            "overall": float (0-1),
            "news": float (0-1),
            "twitter": float (0-1),
            "signal_count": int,
            "positive": int,
            "negative": int,
            "neutral": int,
            "top_signals": List of most significant signals with snippets
        }
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    async with async_session_maker() as session:
        from sqlalchemy import select, and_

        query = select(SentimentSignal).where(
            and_(
                SentimentSignal.company_mentioned == symbol.upper(),
                SentimentSignal.created_at >= cutoff_time,
                SentimentSignal.relevant_to_investors == True
            )
        )

        result = await session.execute(query)
        signals = result.scalars().all()

    if not signals:
        return {
            "overall": 0.5,
            "news": 0.5,
            "twitter": 0.5,
            "signal_count": 0,
            "positive": 0,
            "negative": 0,
            "neutral": 0,
            "top_signals": []
        }

    # Separate by source
    news_signals = []
    twitter_signals = []

    for signal in signals:
        if "twitter" in signal.source.lower():
            twitter_signals.append(signal)
        else:
            news_signals.append(signal)

    # Calculate weighted sentiment
    def calc_sentiment(sigs: List) -> float:
        if not sigs:
            return 0.5

        total_weight = 0
        weighted_sum = 0

        for sig in sigs:
            weight = sig.confidence
            sentiment_val = {"positive": 1.0, "negative": 0.0, "neutral": 0.5}.get(sig.sentiment, 0.5)
            weighted_sum += sentiment_val * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.5

    news_sentiment = calc_sentiment(news_signals)
    twitter_sentiment = calc_sentiment(twitter_signals)

    # Weighted average
    overall = (news_sentiment * NEWS_WEIGHT) + (twitter_sentiment * TWITTER_WEIGHT)

    # Count by sentiment
    counts = {"positive": 0, "negative": 0, "neutral": 0}
    for signal in signals:
        counts[signal.sentiment] += 1

    # Get top 3 most significant signals (by confidence)
    top_signals = sorted(signals, key=lambda s: s.confidence, reverse=True)[:3]
    top_signal_data = [
        {
            "sentiment": s.sentiment,
            "confidence": s.confidence,
            "reason": s.key_reason,
            "snippet": s.snippet or "",
            "title": s.article_title or ""
        }
        for s in top_signals
    ]

    return {
        "overall": overall,
        "news": news_sentiment,
        "twitter": twitter_sentiment,
        "signal_count": len(signals),
        "positive": counts["positive"],
        "negative": counts["negative"],
        "neutral": counts["neutral"],
        "top_signals": top_signal_data
    }


async def generate_predictions(
    symbol: str,
    horizons: List[int] = [3, 7, 14]
) -> StockPrediction:
    """
    Generate multi-horizon price predictions for a stock.

    Args:
        symbol: Stock symbol (e.g., "SCOM")
        horizons: List of prediction horizons in days

    Returns:
        StockPrediction with predictions for each horizon
    """
    # Get current price
    from app.services.nse_prices import get_price

    price_data = await get_price(symbol)
    if not price_data:
        price_data = {"price": 0.0, "change": 0.0, "change_percent": 0.0}

    current_price = price_data.get("price", 0.0)

    # Get aggregated sentiment
    sentiment = await aggregate_sentiment(symbol)

    # Get news and Twitter breakdown
    news_sentiment = sentiment["news"]
    twitter_sentiment = sentiment["twitter"]
    overall_sentiment = sentiment["overall"]

    # Generate predictions for each horizon
    predictions = []

    for horizon in horizons:
        # Base direction from sentiment
        direction = sentiment_to_direction(overall_sentiment)

        # Calculate base confidence
        base_conf = calculate_base_confidence(
            overall_sentiment,
            sentiment["signal_count"]
        )

        # Adjust for horizon
        confidence = adjust_confidence_for_horizon(base_conf, horizon)

        # Apply historical accuracy modifier
        hist_accuracy = await get_historical_accuracy(symbol, horizon)
        confidence *= hist_accuracy

        # Extreme sentiment bonus/penalty
        if overall_sentiment >= 0.80:
            confidence = min(confidence * HIGH_SENTIMENT_BONUS, 0.95)
        elif overall_sentiment <= 0.25:
            confidence = min(confidence * HIGH_SENTIMENT_BONUS, 0.95)

        # Generate reasoning
        reasoning = await generate_prediction_reasoning(
            symbol,
            {
                "overall": overall_sentiment,
                "news": news_sentiment,
                "twitter": twitter_sentiment,
                "signal_count": sentiment["signal_count"]
            },
            horizon,
            direction,
            current_price
        )

        predictions.append(Prediction(
            horizon_days=horizon,
            direction=direction,
            confidence=round(confidence, 2),
            reasoning=reasoning
        ))

    return StockPrediction(
        symbol=symbol.upper(),
        current_price=current_price,
        predictions=predictions,
        overall_sentiment=round(overall_sentiment, 2),
        news_sentiment=round(news_sentiment, 2),
        twitter_sentiment=round(twitter_sentiment, 2),
        signal_count=sentiment["signal_count"],
        last_updated=datetime.utcnow().isoformat()
    )


async def generate_batch_predictions(symbols: List[str]) -> List[StockPrediction]:
    """
    Generate predictions for multiple stocks in parallel.

    Args:
        symbols: List of stock symbols

    Returns:
        List of StockPrediction objects
    """
    import asyncio

    tasks = [generate_predictions(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    predictions = []
    for result in results:
        if isinstance(result, Exception):
            print(f"Error generating prediction: {result}")
        elif result:
            predictions.append(result)

    return predictions


# ============================================================================
# DEMO DATA
# ============================================================================

def get_demo_predictions(symbol: str = "SCOM") -> StockPrediction:
    """Return demo predictions for testing."""
    predictions = [
        Prediction(
            horizon_days=3,
            direction="UP",
            confidence=0.82,
            reasoning="Strong bullish sentiment from 45 signals, M-Pesa growth catalyst supports short-term upside."
        ),
        Prediction(
            horizon_days=7,
            direction="UP",
            confidence=0.74,
            reasoning="Positive sentiment momentum expected to continue, earnings anticipation builds."
        ),
        Prediction(
            horizon_days=14,
            direction="HOLD",
            confidence=0.65,
            reasoning="Longer-term uncertainty amid rate environment; wait for Q1 results."
        ),
    ]

    return StockPrediction(
        symbol=symbol,
        current_price=38.50,
        predictions=predictions,
        overall_sentiment=0.75,
        news_sentiment=0.78,
        twitter_sentiment=0.68,
        signal_count=45,
        last_updated=datetime.utcnow().isoformat()
    )


def get_demo_batch_predictions() -> List[StockPrediction]:
    """Return demo batch predictions for multiple stocks."""
    return [
        get_demo_predictions("SCOM"),
        StockPrediction(
            symbol="EQTY",
            current_price=52.75,
            predictions=[
                Prediction(3, "HOLD", 0.62, "Mixed signals on regional expansion offset rate concerns."),
                Prediction(7, "HOLD", 0.58, "Neutral zone; waiting for clarity on regional strategy."),
                Prediction(14, "DOWN", 0.55, "Medium-term pressure from rising rates expected."),
            ],
            overall_sentiment=0.52,
            news_sentiment=0.55,
            twitter_sentiment=0.45,
            signal_count=28,
            last_updated=datetime.utcnow().isoformat()
        ),
        StockPrediction(
            symbol="KCB",
            current_price=18.20,
            predictions=[
                Prediction(3, "UP", 0.78, "Q3 earnings beat driving positive momentum."),
                Prediction(7, "UP", 0.71, "Post-earnings rally expected to continue."),
                Prediction(14, "HOLD", 0.64, "Longer-term banking sector concerns remain."),
            ],
            overall_sentiment=0.72,
            news_sentiment=0.78,
            twitter_sentiment=0.60,
            signal_count=35,
            last_updated=datetime.utcnow().isoformat()
        ),
    ]


if __name__ == "__main__":
    import asyncio

    async def test():
        pred = await generate_predictions("SCOM")
        print(f"\n{pred.symbol} @ KES {pred.current_price}")
        print(f"Overall Sentiment: {pred.overall_sentiment:.0%}")
        print(f"Signals: {pred.signal_count}")
        print("\nPredictions:")
        for p in pred.predictions:
            print(f"  {p.horizon_days}d: {p.direction} ({p.confidence:.0%}) - {p.reasoning}")

    asyncio.run(test())
