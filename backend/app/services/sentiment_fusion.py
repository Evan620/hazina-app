"""
Sentiment Engine
Uses FinBERT (local) for financial sentiment analysis.
"""

import asyncio
import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

from dotenv import load_dotenv

# Load .env from backend directory
backend_dir = Path(__file__).parent.parent.parent
load_dotenv(backend_dir / ".env")

# Configure logging
logger = logging.getLogger(__name__)

# Model configuration
FINBERT_MODEL = "ProsusAI/finbert"

# FinBERT model cache
_finbert_model = None
_finbert_tokenizer = _finbert_device = None


async def get_fusion_engine():
    """Get the FinBERT model (alias for compatibility)."""
    model, tokenizer, device = get_finbert_model()
    return {
        "model": model,
        "tokenizer": tokenizer,
        "device": device
    }


def get_finbert_model():
    """Load FinBERT model lazily."""
    global _finbert_model, _finbert_tokenizer, _finbert_device

    if _finbert_model is not None:
        return _finbert_model, _finbert_tokenizer, _finbert_device

    try:
        logger.info(f"Loading FinBERT model ({FINBERT_MODEL})...")
        _finbert_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _finbert_tokenizer = AutoTokenizer.from_pretrained(FINBERT_MODEL)
        _finbert_model = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL)
        _finbert_model.to(_finbert_device)
        _finbert_model.eval()
        logger.info(f"FinBERT loaded successfully on {_finbert_device}")
        return _finbert_model, _finbert_tokenizer, _finbert_device
    except Exception as e:
        logger.error(f"Failed to load FinBERT: {e}")
        return None, None, None


# NSE company symbols for matching
NSE_SYMBOLS = {
    # NSE 20 (Large Caps)
    "SCOM": "Safaricom",
    "EQTY": "Equity Group",
    "KCB": "KCB Group",
    "ABSA": "Absa Bank",
    "COOP": "Cooperative Bank",
    "EABL": "East African Breweries",
    "BAT": "British American Tobacco",
    "NMG": "Nation Media Group",
    "JUBH": "Jubilee Holdings",
    "CNTY": "Centum Investment",
    "BAMB": "Bamburi Cement",
    "ARM": "ARM Cement",
    "KAPC": "Kenya Airways",
    "KENG": "KenGen",
    # Add more as needed...
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
            # Make sure it's surrounded by word boundaries
            import re
            pattern = r'\b' + re.escape(symbol) + r'\b'
            if re.search(pattern, text_upper):
                return symbol

    # Then try name match
    for symbol, name in NSE_SYMBOLS.items():
        if name.upper() in text_upper:
            return symbol

    return None


async def analyze_sentiment_finbert(text: str) -> Dict:
    """
    Analyze sentiment using FinBERT (local model).

    Returns:
        {"sentiment": "positive/negative/neutral", "confidence": float}
    """
    model, tokenizer, device = get_finbert_model()

    if model is None:
        logger.warning("FinBERT not available")
        return {"sentiment": "neutral", "confidence": 0.5}

    try:
        # FinBERT labels: positive, negative, neutral
        # Map to our needs
        inputs = tokenizer(text[:512], return_tensors="pt", truncation=True, max_length=512)
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
            confidence, predicted_class_id = torch.max(predictions, dim=-1)
            confidence = confidence.item()
            predicted_class_id = predicted_class_id.item()

        # Map FinBERT labels
        label_mapping = {
            0: "negative",
            1: "neutral",
            2: "positive"
        }

        sentiment = label_mapping.get(predicted_class_id, "neutral")

        logger.info(f"FinBERT: {sentiment} ({confidence:.2%})")

        return {
            "sentiment": sentiment,
            "confidence": round(confidence, 3)
        }

    except Exception as e:
        logger.error(f"FinBERT analysis failed: {e}")
        return {"sentiment": "neutral", "confidence": 0.5}


def extract_relevant_snippet(text: str, company: str, max_length: int = 200) -> str:
    """Extract the most relevant sentence(s) mentioning the company."""
    import re

    # Split into sentences
    sentences = re.split(r'[.!?]+', text)

    # Find sentences mentioning the company
    company_names = [company]
    if company in NSE_SYMBOLS:
        company_names.append(NSE_SYMBOLS[company])

    relevant = []
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20:
            continue
        if any(name.lower() in sent.lower() for name in company_names):
            relevant.append(sent)

    if relevant:
        # Return the first relevant sentence, truncated
        snippet = relevant[0]
        if len(snippet) > max_length:
            snippet = snippet[:max_length] + "..."
        return snippet

    # Fallback: first sentence of article
    first_sent = sentences[0].strip() if sentences else text[:max_length]
    return (first_sent[:max_length] + "...") if len(first_sent) > max_length else first_sent


async def generate_claude_reasoning(
    title: str,
    snippet: str,
    company: str,
    sentiment: str,
    confidence: float
) -> str:
    """Use Claude to explain WHY this sentiment was detected."""
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return f"{sentiment.capitalize()} sentiment detected (confidence: {confidence:.0%})"

    try:
        client = anthropic.Anthropic(api_key=api_key)

        prompt = f"""Explain in ONE concise sentence why this article has {sentiment} sentiment for {company}.

Article Title: {title}
Relevant excerpt: {snippet}
FinBERT confidence: {confidence:.0%}

Focus on the specific words/phrases that drove this sentiment. Return ONLY the explanation sentence."""

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=80,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    except Exception as e:
        logger.error(f"Claude reasoning failed: {e}")
        return f"{sentiment.capitalize()} sentiment detected (confidence: {confidence:.0%})"


async def analyze_article(article: Dict) -> Dict:
    """
    Main entry point: Analyze article using FinBERT.

    Args:
        article: {title, url, source, content?, company?}

    Returns:
        {
            "company_mentioned": "SCOM",
            "sentiment": "positive",
            "confidence": 0.87,
            "source": "finbert",
            "article_title": title,
            "article_url": url,
            "snippet": "relevant text excerpt",
            "key_reason": "Claude explanation"
        }
    """
    title = article.get("title", "")
    content = article.get("content") or article.get("description") or ""
    source = article.get("source", "unknown")
    url = article.get("url", "")

    full_text = f"{title}. {content}" if content else title

    if not full_text or len(full_text) < 50:
        return {
            "company_mentioned": article.get("company"),
            "sentiment": "neutral",
            "confidence": 0.0,
            "source": "none",
            "signal_type": "insufficient",
            "article_title": title,
            "article_url": url,
            "created_at": datetime.utcnow().isoformat()
        }

    # Detect company - use pre-detected if available, otherwise detect from text
    company = article.get("company") or detect_company_strict(full_text)

    # Get sentiment with FinBERT
    sentiment_result = await analyze_sentiment_finbert(full_text)

    # Extract relevant snippet
    snippet = extract_relevant_snippet(full_text, company)

    # Generate Claude reasoning for WHY this sentiment
    reasoning = await generate_claude_reasoning(
        title, snippet, company, sentiment_result["sentiment"], sentiment_result["confidence"]
    )

    return {
        "company_mentioned": company,
        "sentiment": sentiment_result["sentiment"],
        "confidence": sentiment_result["confidence"],
        "key_reason": reasoning,
        "relevant_to_investors": True,
        "source": "finbert",
        "article_title": title,
        "article_url": url,
        "snippet": snippet,
        "created_at": datetime.utcnow().isoformat()
    }


async def save_sentiment_signals(signals: List[Dict]) -> None:
    """Save sentiment signals to database."""
    if not signals:
        return

    from app.db.database import SentimentSignal, async_session_maker

    async with async_session_maker() as session:
        for signal_data in signals:
            if not signal_data.get("company_mentioned"):
                continue

            created_at = signal_data.get("created_at")
            if isinstance(created_at, str):
                from datetime import timedelta
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
                source=signal_data.get("source", ""),
                snippet=signal_data.get("snippet", ""),
                created_at=created_at
            )
            session.add(signal)

        await session.commit()


async def run_news_scraper():
    """
    News scraper using FinBERT.
    """
    from app.services.news_scraper import (
        fetch_business_daily_rss,
        scrape_the_star,
    )

    print(f"[{datetime.utcnow()}] Running news scraper with FinBERT...")
    print("=" * 60)

    all_articles = []

    # Fetch from working sources
    print("📡 Fetching articles...")

    tasks = [
        fetch_business_daily_rss(),
        scrape_the_star(),
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, list):
            all_articles.extend(result)

    print(f"📊 Total articles discovered: {len(all_articles)}")

    # Analyze with FinBERT
    print("🔍 Analyzing with FinBERT...")
    signals = []

    for article in all_articles:
        result = await analyze_article(article)
        if result.get("company_mentioned") and result.get("relevant_to_investors"):
            signals.append(result)
            print(f"   {result.get('company_mentioned', 'Unknown')}: {result.get('sentiment', 'unknown').upper()} ({result.get('confidence', 0):.0%})")

    print(f"\n✅ Generated {len(signals)} sentiment signals")

    # Save to database
    await save_sentiment_signals(signals)

    return signals


# Demo data for testing
def get_demo_sentiment_signals() -> List[Dict]:
    """Return demo sentiment signals for testing."""
    from datetime import timedelta

    return [
        {
            "company_mentioned": "SCOM",
            "sentiment": "positive",
            "confidence": 0.85,
            "key_reason": "Strong M-Pesa growth driven by new merchant onboarding",
            "relevant_to_investors": True,
            "article_url": "https://www.businessdailyafrica.com/corporate/technology/",
            "article_title": "Safaricom M-Pesa merchant numbers grow 20%",
            "source": "Business Daily Africa",
            "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat()
        },
        {
            "company_mentioned": "EQTY",
            "sentiment": "neutral",
            "confidence": 0.72,
            "key_reason": "Regional expansion on track but margin pressure from rising rates",
            "relevant_to_investors": True,
            "article_url": "https://www.businessdailyafrica.com/markets/banking/",
            "article_title": "Equity Group regional expansion faces headwinds",
            "source": "Business Daily Africa",
            "created_at": (datetime.utcnow() - timedelta(hours=4)).isoformat()
        },
        {
            "company_mentioned": "KCB",
            "sentiment": "positive",
            "confidence": 0.78,
            "key_reason": "Q3 earnings beat expectations on loan book growth",
            "relevant_to_investors": True,
            "article_url": "https://www.the-star.co.ke/business/",
            "article_title": "KCB Group Q3 profit rises 15%",
            "source": "The Star Kenya",
            "created_at": (datetime.utcnow() - timedelta(hours=6)).isoformat()
        },
        {
            "company_mentioned": "ABSA",
            "sentiment": "positive",
            "confidence": 0.82,
            "key_reason": "Consumer finance unit posts strong revenue and profit growth",
            "relevant_to_investors": True,
            "article_url": "https://www.businessdailyafrica.com/",
            "article_title": "Absa consumer finance unit posts revenue, profit growth",
            "source": "FinBERT Analysis",
            "created_at": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        },
    ]


if __name__ == "__main__":
    asyncio.run(run_news_scraper())
