"""
Twitter/X API Scraper for NSE Stock Sentiment
Uses Twitter API v2 for reliable, rate-limited data fetching.
"""

import os
import tweepy
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

from app.db.database import SentimentSignal, async_session_maker
from app.services.sentiment_fusion import get_fusion_engine, NSE_SYMBOLS


# ============================================================================
# CONFIGURATION
# ============================================================================

# Twitter API v2 credentials (OAuth 1.0a)
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET")

# NSE stock symbols for Twitter search
# Users search with $SYMBOL (e.g., $SCOM, $EQTY)
NSE_SYMBOLS_WITH_DOLLAR = {f"${symbol}": name for symbol, name in NSE_SYMBOLS.items()}

# Noise filtering patterns
SPAM_KEYWORDS = [
    "moon", "lambo", "100x", "1000x", "gem", "diamond hands",
    "paper hands", "ape", "hodl", "to the moon", "rocket ship",
    "giveaway", "airdrop", "free money", "get rich quick",
    "pump and dump", "pnd", "guaranteed", "risk free"
]

LOW_QUALITY_PATTERNS = [
    r"^(buy|sell)\s+\$\w+\s*!*$",  # Just "BUY $SCOM!"
    r"\$\w+\s*(is|are)\s*(good|bad)\s*!*$",  # Too simple
    r"^\$\w+\s*!!!*$",  # Just symbol + exclamations
]

# Minimum engagement thresholds (helps filter bots)
MIN_FOLLOWERS = 50
MIN_LIKES = 1


# ============================================================================
# TWITTER API CLIENT
# ============================================================================

def get_twitter_client():
    """Get authenticated Twitter API v2 client using OAuth 1.0a credentials."""
    required = [TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]
    if not all(required):
        raise ValueError("All Twitter credentials (API_KEY, API_SECRET, ACCESS_TOKEN, ACCESS_SECRET) must be set")

    return tweepy.Client(
        consumer_key=TWITTER_API_KEY,
        consumer_secret=TWITTER_API_SECRET,
        access_token=TWITTER_ACCESS_TOKEN,
        access_token_secret=TWITTER_ACCESS_SECRET,
        wait_on_rate_limit=True
    )


# ============================================================================
# NOISE FILTERING
# ============================================================================

def is_spam_tweet(text: str) -> bool:
    """Check if tweet contains spam keywords."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SPAM_KEYWORDS)


def is_low_quality(text: str) -> bool:
    """Check if tweet is too low quality to analyze."""
    # Very short tweets
    if len(text.strip()) < 15:
        return True

    # Check against low quality patterns
    for pattern in LOW_QUALITY_PATTERNS:
        if re.match(pattern, text.lower(), re.IGNORECASE):
            return True

    return False


def is_bot_like(author: Dict) -> bool:
    """Check if author appears to be a bot based on public metrics."""
    # New account (less than 30 days)
    if author.get("created_at"):
        try:
            created = datetime.fromisoformat(author["created_at"].replace("Z", "+00:00"))
            if (datetime.utcnow() - created) < timedelta(days=30):
                return True
        except:
            pass

    # Very low follower count
    followers = author.get("followers_count", 0)
    if followers < MIN_FOLLOWERS:
        return True

    # Suspicious follower/following ratio
    following = author.get("following_count", 0)
    if followers > 0 and following / followers > 10:
        return True

    return False


def is_duplicate(tweets_seen: set, text: str) -> bool:
    """Check if this is a duplicate tweet (from same user, similar content)."""
    # Simple duplicate detection by exact text match
    normalized = text.strip().lower()
    if normalized in tweets_seen:
        return True

    tweets_seen.add(normalized)
    return False


def calculate_quality_score(tweet: Dict) -> float:
    """
    Calculate a quality score for a tweet (0-1).
    Higher = more reliable for sentiment analysis.
    """
    score = 0.5  # Base score

    # Engagement bonus
    public_metrics = tweet.get("public_metrics", {})
    likes = public_metrics.get("like_count", 0)
    retweets = public_metrics.get("retweet_count", 0)
    replies = public_metrics.get("reply_count", 0)
    quotes = public_metrics.get("quote_count", 0)

    # Engagement increases quality
    engagement = likes + (retweets * 2) + (replies * 1.5) + (quotes * 2)
    score += min(engagement / 100, 0.3)

    # Author follower bonus
    author = tweet.get("author_data", {})
    followers = author.get("followers_count", 0)
    if followers > 1000:
        score += 0.1
    elif followers > 10000:
        score += 0.2

    # Verified account bonus
    if author.get("verified", False):
        score += 0.1

    return min(score, 1.0)


# ============================================================================
# TWITTER FETCHING
# ============================================================================

async def fetch_tweets_for_symbol(symbol: str, max_results: int = 100) -> List[Dict]:
    """
    Fetch recent tweets mentioning an NSE stock symbol.

    Args:
        symbol: Stock symbol (e.g., "SCOM")
        max_results: Maximum tweets to fetch (API limit: 100 per request)

    Returns:
        List of tweet dictionaries with text, author, metrics
    """
    try:
        client = get_twitter_client()

        # Search for $SYMBOL tweets
        query = f"${symbol} (lang:en OR lang:sw) -is:retweet"
        exclude = ["retweets", "replies"]

        response = client.search_recent_tweets(
            query=query,
            max_results=min(max_results, 100),
            tweet_fields=["created_at", "public_metrics", "author_id", "lang", "text"],
            user_fields=["created_at", "public_metrics", "verified", "username"],
            expansions=["author_id"],
            exclude=exclude
        )

        tweets = []
        if response.data:
            # Build author lookup
            authors = {}
            if response.includes and "users" in response.includes:
                for user in response.includes["users"]:
                    authors[user.id] = {
                        "id": user.id,
                        "username": user.username,
                        "verified": user.verified,
                        "followers_count": user.public_metrics["followers_count"],
                        "following_count": user.public_metrics["following_count"],
                        "created_at": user.created_at.isoformat() if user.created_at else None
                    }

            # Process tweets
            for tweet in response.data:
                author_data = authors.get(tweet.author_id, {})
                tweets.append({
                    "id": tweet.id,
                    "text": tweet.text,
                    "created_at": tweet.created_at.isoformat() if tweet.created_at else None,
                    "public_metrics": tweet.public_metrics,
                    "author_id": tweet.author_id,
                    "author_data": author_data,
                    "symbol": symbol
                })

        print(f"[Twitter] Found {len(tweets)} tweets for ${symbol}")
        return tweets

    except tweepy.Errors.TooManyRequests:
        print(f"[Twitter] Rate limit exceeded for ${symbol}")
        return []
    except tweepy.Errors.Forbidden:
        print(f"[Twitter] Access forbidden - check API credentials")
        return []
    except Exception as e:
        print(f"[Twitter] Error fetching tweets for ${symbol}: {e}")
        return []


async def fetch_all_nse_tweets(max_per_symbol: int = 50) -> List[Dict]:
    """
    Fetch tweets for all NSE companies.

    Args:
        max_per_symbol: Max tweets to fetch per symbol

    Returns:
        List of filtered, quality tweets
    """
    print(f"[{datetime.utcnow()}] Fetching Twitter data for NSE stocks...")
    print("=" * 60)

    all_tweets = []
    tweets_seen = set()

    # Limit to major NSE stocks for API efficiency
    major_symbols = ["SCOM", "EQTY", "KCB", "ABSA", "EABL", "COOP", "NMG", "JUBH", "CNTY"]

    for symbol in major_symbols:
        tweets = await fetch_tweets_for_symbol(symbol, max_per_symbol)

        # Apply noise filters
        for tweet in tweets:
            text = tweet["text"]
            author = tweet.get("author_data", {})

            # Skip if spam
            if is_spam_tweet(text):
                continue

            # Skip if low quality
            if is_low_quality(text):
                continue

            # Skip if bot-like
            if is_bot_like(author):
                continue

            # Skip duplicates
            if is_duplicate(tweets_seen, text):
                continue

            # Calculate quality score
            tweet["quality_score"] = calculate_quality_score(tweet)

            all_tweets.append(tweet)

        print(f"   ${symbol}: {len(tweets)} raw → {len([t for t in tweets if t in all_tweets])} after filtering")

    print(f"\n✅ Total quality tweets collected: {len(all_tweets)}")
    return all_tweets


# ============================================================================
# SENTIMENT ANALYSIS
# ============================================================================

async def analyze_twitter_sentiment(tweets: List[Dict]) -> List[Dict]:
    """
    Analyze sentiment of Twitter posts using the fusion engine.

    Args:
        tweets: List of tweet dictionaries

    Returns:
        List of sentiment signals
    """
    if not tweets:
        return []

    print("\n🧠 Running Twitter sentiment analysis...")

    fusion_engine = get_fusion_engine()
    signals = []

    # Group tweets by symbol for batch processing
    by_symbol = {}
    for tweet in tweets:
        symbol = tweet["symbol"]
        if symbol not in by_symbol:
            by_symbol[symbol] = []
        by_symbol[symbol].append(tweet)

    for symbol, symbol_tweets in by_symbol.items():
        # Calculate aggregate sentiment from multiple tweets
        sentiments = {"positive": 0, "negative": 0, "neutral": 0}
        total_confidence = 0
        weighted_reasons = []

        for tweet in symbol_tweets:
            # Analyze individual tweet
            article_format = {
                "title": tweet["text"][:100] + "..." if len(tweet["text"]) > 100 else tweet["text"],
                "content": tweet["text"],
                "url": f"https://twitter.com/i/web/status/{tweet['id']}",
                "source": "Twitter/X",
                "teaser": tweet["text"],
                "company": symbol
            }

            result = await fusion_engine.analyze_article(article_format)
            if result:
                sentiment = result.get("sentiment", "neutral")
                sentiments[sentiment] += 1

                confidence = result.get("confidence", 0.5)
                quality = tweet.get("quality_score", 0.5)

                # Weight by quality
                total_confidence += confidence * quality

                if result.get("key_reason"):
                    weighted_reasons.append(result["key_reason"])

        # Determine overall sentiment for this symbol
        total = sum(sentiments.values())
        if total > 0:
            # Calculate weighted sentiment
            positive_ratio = sentiments["positive"] / total
            negative_ratio = sentiments["negative"] / total

            if positive_ratio > negative_ratio and positive_ratio > 0.5:
                overall = "positive"
            elif negative_ratio > positive_ratio and negative_ratio > 0.5:
                overall = "negative"
            else:
                overall = "neutral"

            avg_confidence = min(total_confidence / total, 1.0)

            # Combine reasons
            key_reason = "; ".join(weighted_reasons[:3]) if weighted_reasons else f"Twitter sentiment on ${symbol}"

            signals.append({
                "company_mentioned": symbol,
                "sentiment": overall,
                "confidence": avg_confidence,
                "key_reason": f"Twitter: {key_reason}",
                "relevant_to_investors": True,
                "article_url": f"https://twitter.com/search?q=${symbol}",
                "article_title": f"${symbol} Twitter sentiment ({total} tweets analyzed)",
                "source": "Twitter/X",
                "created_at": datetime.utcnow().isoformat(),
                "tweet_count": total,
                "sentiment_breakdown": sentiments
            })

            print(f"   ${symbol}: {overall.upper()} ({avg_confidence:.0%}) - {total} tweets")

    return signals


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

async def run_twitter_scraper() -> List[Dict]:
    """
    Main Twitter scraper - fetches tweets and analyzes sentiment.

    Returns:
        List of sentiment signals ready for database storage
    """
    print(f"[{datetime.utcnow()}] Running Twitter sentiment scraper...")
    print("=" * 60)

    # Fetch tweets
    tweets = await fetch_all_nse_tweets()

    if not tweets:
        print("⚠️ No tweets collected. Check TWITTER_BEARER_TOKEN.")
        return []

    # Analyze sentiment
    signals = await analyze_twitter_sentiment(tweets)

    if signals:
        # Save to database
        await save_sentiment_signals(signals)

    return signals


async def save_sentiment_signals(signals: List[Dict]) -> None:
    """Save Twitter sentiment signals to database."""
    if not signals:
        return

    async with async_session_maker() as session:
        for signal_data in signals:
            created_at = signal_data.get("created_at")
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            else:
                created_at = datetime.utcnow()

            signal = SentimentSignal(
                company_mentioned=signal_data.get("company_mentioned", ""),
                sentiment=signal_data.get("sentiment", "neutral"),
                confidence=signal_data.get("confidence", 0.5),
                key_reason=signal_data.get("key_reason", ""),
                relevant_to_investors=signal_data.get("relevant_to_investors", True),
                article_url=signal_data.get("article_url", ""),
                article_title=signal_data.get("article_title", ""),
                source=signal_data.get("source", "Twitter/X"),
                created_at=created_at
            )
            session.add(signal)

        await session.commit()
        print(f"\n💾 Saved {len(signals)} Twitter signals to database")


# ============================================================================
# DEMO DATA
# ============================================================================

def get_demo_twitter_signals() -> List[Dict]:
    """Return demo Twitter sentiment signals for testing (when API unavailable)."""
    return [
        {
            "company_mentioned": "SCOM",
            "sentiment": "positive",
            "confidence": 0.82,
            "key_reason": "Twitter: Strong M-Pesa growth discussion, dividend expectations positive",
            "relevant_to_investors": True,
            "article_url": "https://twitter.com/search?q=$SCOM",
            "article_title": "$SCOM Twitter sentiment (45 tweets analyzed)",
            "source": "Twitter/X",
            "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat(),
            "tweet_count": 45,
            "sentiment_breakdown": {"positive": 32, "negative": 5, "neutral": 8}
        },
        {
            "company_mentioned": "EQTY",
            "sentiment": "neutral",
            "confidence": 0.65,
            "key_reason": "Twitter: Mixed views on regional expansion, rate concerns",
            "relevant_to_investors": True,
            "article_url": "https://twitter.com/search?q=$EQTY",
            "article_title": "$EQTY Twitter sentiment (28 tweets analyzed)",
            "source": "Twitter/X",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "tweet_count": 28,
            "sentiment_breakdown": {"positive": 10, "negative": 8, "neutral": 10}
        },
        {
            "company_mentioned": "KCB",
            "sentiment": "positive",
            "confidence": 0.74,
            "key_reason": "Twitter: Q3 earnings beat discussed positively, dividend talk",
            "relevant_to_investors": True,
            "article_url": "https://twitter.com/search?q=$KCB",
            "article_title": "$KCB Twitter sentiment (35 tweets analyzed)",
            "source": "Twitter/X",
            "created_at": (datetime.utcnow() - timedelta(hours=3)).isoformat(),
            "tweet_count": 35,
            "sentiment_breakdown": {"positive": 22, "negative": 6, "neutral": 7}
        },
    ]


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_twitter_scraper())
