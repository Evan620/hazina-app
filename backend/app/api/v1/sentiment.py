"""
Sentiment analysis endpoints
NLP-driven market sentiment from Kenyan news sources
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
from datetime import datetime, timedelta
from typing import List, Optional

from app.db.database import get_db, SentimentSignal

router = APIRouter()


@router.get("/signals")
async def get_sentiment_signals(
    symbol: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get latest sentiment signals for NSE equities.
    Returns bulllish/bearish/neutral signals with confidence scores.
    """
    # Get signals from last 48 hours
    cutoff_time = datetime.utcnow() - timedelta(hours=48)

    query = select(SentimentSignal).where(
        and_(
            SentimentSignal.created_at >= cutoff_time,
            SentimentSignal.relevant_to_investors == True
        )
    )

    if symbol:
        query = query.where(SentimentSignal.company_mentioned == symbol.upper())

    query = query.order_by(desc(SentimentSignal.created_at)).limit(limit)

    result = await db.execute(query)
    signals = result.scalars().all()

    # Aggregate by company for summary
    company_signals = {}
    for signal in signals:
        company = signal.company_mentioned
        if company not in company_signals:
            company_signals[company] = {
                "symbol": company,
                "signals": [],
                "sentiment_counts": {"positive": 0, "negative": 0, "neutral": 0},
                "avg_confidence": 0,
                "latest": None
            }

        company_signals[company]["signals"].append({
            "sentiment": signal.sentiment,
            "confidence": signal.confidence,
            "reason": signal.key_reason,
            "source": signal.source,
            "article_url": signal.article_url,
            "created_at": signal.created_at.isoformat()
        })

        company_signals[company]["sentiment_counts"][signal.sentiment] += 1
        company_signals[company]["avg_confidence"] += signal.confidence

        if not company_signals[company]["latest"] or signal.created_at > company_signals[company]["latest"]:
            company_signals[company]["latest"] = signal.created_at.isoformat()

    # Calculate averages and determine overall sentiment
    for data in company_signals.values():
        signal_count = len(data["signals"])
        if signal_count > 0:
            data["avg_confidence"] = round(data["avg_confidence"] / signal_count, 2)

        # Determine overall sentiment badge
        counts = data["sentiment_counts"]
        if counts["positive"] > counts["negative"]:
            data["overall_sentiment"] = "bullish"
        elif counts["negative"] > counts["positive"]:
            data["overall_sentiment"] = "bearish"
        else:
            data["overall_sentiment"] = "neutral"

    return {
        "signals": list(company_signals.values()),
        "as_of": datetime.utcnow().isoformat(),
        "source": "Kenyan news NLP (Business Daily, Reuters Africa, The Star)",
        "note": "Sentiment derived from publicly available news articles"
    }


@router.get("/feed")
async def get_sentiment_feed(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get chronological feed of sentiment signals.
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=72)

    query = (
        select(SentimentSignal)
        .where(SentimentSignal.created_at >= cutoff_time)
        .order_by(desc(SentimentSignal.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    signals = result.scalars().all()

    return {
        "feed": [
            {
                "company": s.company_mentioned,
                "sentiment": s.sentiment,
                "confidence": s.confidence,
                "reason": s.key_reason,
                "source": s.source,
                "article_title": s.article_title,
                "article_url": s.article_url,
                "created_at": s.created_at.isoformat()
            }
            for s in signals
        ],
        "source": "Kenyan news aggregation + NLP"
    }


@router.get("/summary/{symbol}")
async def get_company_sentiment(
    symbol: str,
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """
    Get sentiment summary for a specific company over N days.
    """
    cutoff_time = datetime.utcnow() - timedelta(days=days)

    query = (
        select(SentimentSignal)
        .where(
            and_(
                SentimentSignal.company_mentioned == symbol.upper(),
                SentimentSignal.created_at >= cutoff_time
            )
        )
        .order_by(desc(SentimentSignal.created_at))
    )

    result = await db.execute(query)
    signals = result.scalars().all()

    if not signals:
        return {
            "symbol": symbol.upper(),
            "message": "No sentiment data found for this company",
            "suggestion": "Try increasing the time range or check if the symbol is correct"
        }

    # Calculate summary stats
    total = len(signals)
    positive = sum(1 for s in signals if s.sentiment == "positive")
    negative = sum(1 for s in signals if s.sentiment == "negative")
    neutral = sum(1 for s in signals if s.sentiment == "neutral")
    avg_confidence = round(sum(s.confidence for s in signals) / total, 2)

    # Determine overall
    if positive > negative:
        overall = "bullish"
    elif negative > positive:
        overall = "bearish"
    else:
        overall = "neutral"

    return {
        "symbol": symbol.upper(),
        "period_days": days,
        "overall_sentiment": overall,
        "signal_count": total,
        "breakdown": {
            "positive": positive,
            "negative": negative,
            "neutral": neutral
        },
        "avg_confidence": avg_confidence,
        "latest_signals": [
            {
                "sentiment": s.sentiment,
                "confidence": s.confidence,
                "reason": s.key_reason,
                "source": s.source,
                "created_at": s.created_at.isoformat()
            }
            for s in signals[:5]
        ]
    }
