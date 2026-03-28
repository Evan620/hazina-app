"""
Claude-First Sentiment Engine
Uses Claude API for all analysis: sentiment, company detection, and financial context
Best for English/Swahili mixed financial news
"""

import os
import anthropic
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load .env from backend directory
backend_dir = Path(__file__).parent.parent.parent
load_dotenv(backend_dir / ".env")

# Configure logging
logger = logging.getLogger(__name__)

# Claude API
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# NSE company symbols for matching (more strict matching)
NSE_SYMBOLS = {
    # NSE 20 (Large Caps) - use full names for better matching
    "SCOM": "Safaricom",
    "EQTY": "Equity Group",
    "EQTY": "Equity Bank",
    "KCB": "KCB Group",
    "KCB": "KCB Bank",
    "ABSA": "Absa Bank",
    "ABSA": "Absa Kenya",
    "COOP": "Cooperative Bank",
    "EABL": "East African Breweries",
    "EABL": "EABL",
    "BAT": "British American Tobacco",
    "NMG": "Nation Media Group",
    "JUBH": "Jubilee Holdings",
    "CNTY": "Centum Investment",
    "BAMB": "Bamburi Cement",
    "ARM": "ARM Cement",
    "KAPC": "Kenya Airways",
    "KENG": "KenGen",
    "TKN": "Telkom Kenya",
    "DTK": "Diamond Trust Bank",
    "HFCK": "Housing Finance",
    "ICDC": "Investments & Securities",
    "CIC": "CIC Insurance",
    "BRITAM": "Britam",
    "ATHI": "Athiya Mining",
    "BAMB": "Bamburi",
    "BA": "British American",
}


def detect_company_strict(text: str) -> Optional[str]:
    """
    Strict company detection - must match full name or exact symbol.
    Reduces false positives like "Bamboo" → BAMB.
    """
    text_upper = text.upper()

    # First try exact symbol match
    for symbol, name in NSE_SYMBOLS.items():
        if symbol in text_upper:
            # Make sure it's surrounded by word boundaries or common punctuation
            import re
            pattern = r'\b' + re.escape(symbol) + r'\b'
            if re.search(pattern, text_upper):
                return symbol

    # Then try name match (more strict)
    for symbol, name in NSE_SYMBOLS.items():
        if name.upper() in text_upper:
            return symbol

    return None


async def analyze_with_claude(article: Dict) -> Dict:
    """
    Use Claude API for complete sentiment analysis.
    Handles English, Swahili, and mixed content.
    """
    title = article.get("title", "")
    content = article.get("content") or article.get("description") or ""
    source = article.get("source", "unknown")
    url = article.get("url", "")

    full_text = f"{title}. {content}" if content else title

    if not full_text or len(full_text) < 50:
        return {
            "company_mentioned": None,
            "sentiment": "neutral",
            "confidence": 0.0,
            "key_reason": "Insufficient content to analyze",
            "relevant_to_investors": False,
            "source": "claude",
            "signal_type": "insufficient",
            "article_title": title,
            "article_url": url,
            "created_at": datetime.utcnow().isoformat()
        }

    # Build prompt for Claude
    prompt = f"""Analyze this financial news article for the Nairobi Securities Exchange (NSE).

Article: {full_text}
Source: {source}

Provide analysis in JSON format:
{{
  "company_mentioned": "NSE symbol (SCOM, EQTY, KCB, etc.) or null if no NSE company mentioned",
  "sentiment": "positive/negative/neutral",
  "confidence": 0.0 to 1.0,
  "signal_type": "earnings/guidance/m&a/market/commentary/other",
  "key_reason": "Brief explanation (1 sentence) of why this sentiment makes sense for investors",
  "relevant_to_investors": true/false,
  "entities": ["list of company names mentioned"]
}}

Important:
- Only mark as relevant if it contains actual investor-useful information (earnings, strategy, mergers, guidance, etc.)
- "Revenue growth", "profit increase", "dividend declared" = positive
- "Loss", "decline", "layoffs", "regulatory issues" = negative
- General news without investor impact = neutral
- Be confident when signals are clear, conservative when ambiguous
- Handle Swahili/Sheng mixed with English appropriately
- If no clear NSE company is mentioned, return null for company_mentioned
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            temperature=0.2,  # Lower temperature for consistent analysis
            messages=[{"role": "user", "content": prompt}]
        )

        import json
        response_text = response.content[0].text

        # Extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)

        # Verify company mentioned (double-check with our strict matcher)
        detected_company = result.get("company_mentioned")
        if detected_company:
            verified_company = detect_company_strict(full_text)
            if not verified_company:
                # Claude detected a company but our strict check failed
                # Use Claude's detection but flag it
                logger.warning(f"Claude detected {detected_company} but strict matcher didn't confirm")
            else:
                detected_company = verified_company

        return {
            "company_mentioned": detected_company,
            "sentiment": result.get("sentiment", "neutral"),
            "confidence": round(result.get("confidence", 0.5), 3),
            "key_reason": result.get("key_reason", "Analysis complete"),
            "relevant_to_investors": result.get("relevant_to_investors", True),
            "source": "claude",
            "signal_type": result.get("signal_type", "commentary"),
            "entities_detected": result.get("entities", []),
            "article_title": title,
            "article_url": url,
            "created_at": datetime.utcnow().isoformat()
        }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response: {e}")
        return {
            "company_mentioned": None,
            "sentiment": "neutral",
            "confidence": 0.0,
            "key_reason": "Analysis failed - JSON error",
            "relevant_to_investors": False,
            "source": "claude-error",
            "signal_type": "error",
            "article_title": title,
            "article_url": url,
            "created_at": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Claude analysis failed: {e}")
        return {
            "company_mentioned": None,
            "sentiment": "neutral",
            "confidence": 0.0,
            "key_reason": f"Analysis failed: {str(e)}",
            "relevant_to_investors": False,
            "source": "claude-error",
            "signal_type": "error",
            "article_title": title,
            "article_url": url,
            "created_at": datetime.utcnow().isoformat()
        }


async def run_news_scraper_claude():
    """
    News scraper using Claude-first sentiment analysis.
    """
    from app.services.news_scraper import (
        fetch_business_daily_rss,
        scrape_the_star,
        NSE_SYMBOLS
    )

    print(f"[{datetime.utcnow()}] Running news scraper with Claude-first analysis...")
    print("=" * 60)

    all_articles = []

    # Fetch from working sources
    print("📡 Fetching articles...")

    tasks = [
        fetch_business_daily_rss(),
        scrape_the_star(),
    ]

    import asyncio
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)

    print(f"📊 Total articles discovered: {len(all_articles)}")

    # Filter for NSE companies (using Claude, not keyword matching)
    print("🔍 Analyzing articles with Claude...")
    nse_articles = []
    signals = []

    for article in all_articles:
        # Use Claude to analyze
        result = await analyze_with_claude(article)

        # Only save if company was mentioned and it's investor-relevant
        if result.get("company_mentioned") and result.get("relevant_to_investors"):
            signals.append(result)
            print(f"   {result.get('company_mentioned', 'Unknown')}: {result.get('sentiment', 'unknown').upper()} ({result.get('confidence', 0):.0%}) - {result.get('key_reason', '')[:50]}...")

    print(f"\n✅ Generated {len(signals)} sentiment signals")

    # Save to database
    from app.services.news_scraper import save_sentiment_signals
    await save_sentiment_signals(signals)

    return signals


# Singleton for backwards compatibility
async def get_sentiment_engine():
    """Return placeholder for compatibility with existing code."""
    return None


if __name__ == "__main__":
    asyncio.run(run_news_scraper_claude())
