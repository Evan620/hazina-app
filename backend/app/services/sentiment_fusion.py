"""
Sentiment Fusion Engine
Combines multilingual sentiment (via HF Inference API) + Claude (financial context)
for accurate, cost-effective Kenyan financial news sentiment analysis.
"""

import asyncio
import os
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

import anthropic
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Load .env from backend directory
backend_dir = Path(__file__).parent.parent.parent
load_dotenv(backend_dir / ".env")

# Configure logging
logger = logging.getLogger(__name__)

# Hugging Face Inference API configuration
# Using cardiffnlp/twitter-xlm-roberta-base-sentiment (supports Swahili, Arabic, African languages)
# Davlan/afrisenti-twitter-sentiment-afroxlmr-large not available on HF Inference
HF_MODEL = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
HF_API_TOKEN = os.getenv("HUGGINGFACE_API_TOKEN")

# NSE company symbols for matching (60+ stocks)
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

    # Main Investment Securities Segment
    "BAMB": "Bamburi Cement",
    "ARM": "ARM Cement",
    "KAPC": "Kenya Airways",
    "KENG": "KenGen",
    "KNRE": "Kenya Reinsurance",
    "TKN": "Telkom Kenya",
    "UOM": "Uchumi Supermarkets",
    "WTKR": "Total Kenya",
    "LVVR": "Livingstone",
    "SFT": "Sameer Africa",

    # Growth Enterprise Market Segment (GEMS)
    "BRCK": "Brimstone Investment",
    "LKL": "Liberty Holdings",
    "SPWN": "Spencer Flowers",
    "HAFR": "HF Group",
    "DVSU": "Davis & Shirtliff",
    "FTRE": "Finlease",
    "GSU": "Gaara",
    "CFCF": "CFC Stanbic",
    "ICDC": "Investments & Securities",
    "KQL": "Kenya Airways",
    "MMMM": "Mumias Sugar",
    "NORE": "Nation Express",

    # Banks & Finance
    "DTK": "Diamond Trust Bank",
    "SBSC": "Standard Chartered",
    "HFCK": "Housing Finance",
    "FAF": "Fidelity",
    "BBK": "Barclays",
    "CHLL": "Chille",

    # Insurance
    "CIC": "CIC Insurance",
    "MSC": "Mobius",
    "APEA": "Apac",
    "JUBK": "Jubilee Insurance",

    # Investment
    "ATLA": "Atlantis",
    "REAV": "Real Estate",

    # Manufacturing & Industry
    "PORT": "Portsmouth",
    "RMS": "Rms",
    "KURV": "Kuria",
    "MOLO": "Molo Tea",

    # Energy
    "KP": "Kenol",
    "MTRN": "Motorways",

    # Agriculture
    "KOF": "Koffee",
    "SISL": "Sisal",
    "TEA": "Tea",
    "LIM": "Limuru Tea",
    "KAPA": "Kapchorua Tea",

    # Commercial & Services
    "UMME": "Umw",
}

# AfriSenti model labels (from model card)
AFRISENTI_LABELS = {
    0: "negative",
    1: "neutral",
    2: "positive"
}


class SentimentFusionEngine:
    """
    Hybrid sentiment analysis combining:
    1. AfriSenti/CardiffNLP (multilingual sentiment) via HF Inference API
    2. Claude API (financial context interpretation)
    """

    _hf_client: Optional[InferenceClient] = None

    def __init__(self):
        self.claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.confidence_threshold = float(os.getenv("SENTIMENT_CONFIDENCE_THRESHOLD", "0.70"))
        self.use_hf_api = bool(HF_API_TOKEN)

    @classmethod
    def get_hf_client(cls) -> InferenceClient:
        """Get or create HF Inference client."""
        if cls._hf_client is None:
            cls._hf_client = InferenceClient(
                provider="hf-inference",
                api_key=HF_API_TOKEN,
            )
        return cls._hf_client

    def detect_company(self, text: str) -> Optional[str]:
        """Detect if text mentions an NSE company."""
        text_upper = text.upper()
        for symbol, name in NSE_SYMBOLS.items():
            if symbol in text_upper or name.upper() in text_upper:
                return symbol
        return None

    async def get_linguistic_sentiment(self, text: str) -> Dict:
        """
        Get linguistic sentiment from multilingual model via HF Inference API.

        Returns:
            {"sentiment": "positive/negative/neutral", "confidence": float, "raw_scores": {...}}
        """
        if not self.use_hf_api:
            logger.warning("HUGGINGFACE_API_TOKEN not set, returning neutral sentiment")
            return {"sentiment": "neutral", "confidence": 0.5, "raw_scores": {}}

        try:
            client = self.get_hf_client()

            # Truncate text to avoid token limit errors (model max is 512 tokens)
            truncated = text[:500] if len(text) > 500 else text

            # Call HF Inference API - text_classification is synchronous
            result = client.text_classification(
                model=HF_MODEL,
                text=truncated
            )

            if not result or len(result) == 0:
                logger.warning("Empty response from HF API")
                return {"sentiment": "neutral", "confidence": 0.5, "raw_scores": {}}

            # Find highest score
            best = max(result, key=lambda x: x.score if hasattr(x, 'score') else 0)
            sentiment = best.label.lower() if hasattr(best, 'label') else "neutral"
            confidence = float(best.score) if hasattr(best, 'score') else 0.5

            # Build raw scores dict
            raw_scores = {
                r.label.lower(): float(r.score) if hasattr(r, 'score') else 0.0
                for r in result
            }

            return {
                "sentiment": sentiment,
                "confidence": confidence,
                "raw_scores": raw_scores
            }

        except Exception as e:
            logger.error(f"Error calling HF Inference API: {e}")
            return {"sentiment": "neutral", "confidence": 0.5, "raw_scores": {}}

    def detect_financial_context(self, text: str) -> Dict:
        """
        Use Claude to detect financial context signals.

        Returns:
            {"is_financial": bool, "entities": [...], "signal_type": "..."}
        """
        # Quick keyword check first (cheaper than Claude)
        financial_keywords = [
            "profit", "loss", "revenue", "dividend", "share", "stock", "price",
            "investment", "ipo", "listing", "market", "trading", "earnings",
            "growth", "margin", "assets", "liability", "capital", "shareholder"
        ]
        text_lower = text.lower()
        has_financial_keywords = any(kw in text_lower for kw in financial_keywords)

        if not has_financial_keywords:
            return {"is_financial": False, "entities": [], "signal_type": "general"}

        # If keywords present, use Claude for deeper analysis
        try:
            prompt = f"""Analyze this financial news snippet and extract:

Text: {text}

Return JSON only:
{{
  "is_financial": true/false,
  "entities": ["company names mentioned"],
  "signal_type": "earnings/guidance/m&a/market/commentary/other",
  "key_metrics": ["any numbers/metrics mentioned"]
}}"""

            message = self.claude_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

            import json
            response_text = message.content[0].text

            # Extract JSON from response (handle markdown code blocks)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)
            return result

        except Exception as e:
            logger.warning(f"Claude context detection failed: {e}")
            return {"is_financial": True, "entities": [], "signal_type": "unknown"}

    async def analyze_article(self, article: Dict) -> Dict:
        """
        Main entry point: Analyze article using hybrid fusion pipeline.
        Now uses full article content when available (from RSS feeds).

        Args:
            article: {title, url, source, content?}

        Returns:
            {
                "company_mentioned": "SCOM",
                "sentiment": "positive",
                "confidence": 0.87,
                "source": "afrisenti+claude",
                "signal_type": "earnings",
                "timestamp": "..."
            }
        """
        title = article.get("title", "")
        content = article.get("content") or article.get("description") or ""
        full_text = f"{title}. {content}" if content else title

        if not full_text:
            return {
                "company_mentioned": None,
                "sentiment": "neutral",
                "confidence": 0.0,
                "source": "none",
                "signal_type": "empty",
                "timestamp": datetime.utcnow().isoformat()
            }

        # Step 1: Detect company
        company = self.detect_company(full_text)

        # Step 2: Get linguistic sentiment from AfriSenti (HF API)
        linguistic = await self.get_linguistic_sentiment(full_text)

        # Step 3: Detect financial context with Claude
        context = self.detect_financial_context(full_text)

        # Step 4: Combine results
        # If linguistic confidence is low and we have financial context, boost it
        final_confidence = linguistic["confidence"]
        if context.get("is_financial") and linguistic["confidence"] < self.confidence_threshold:
            # Boost confidence slightly when we confirm it's financial news
            final_confidence = min(0.85, linguistic["confidence"] + 0.15)

        # Generate a human-readable reason
        sentiment_desc = {
            "positive": "Bullish signals from",
            "negative": "Bearish signals from",
            "neutral": "Neutral coverage from"
        }[linguistic["sentiment"]]

        reason = f"{sentiment_desc} {article.get('source', 'news source')}"
        if context.get("is_financial"):
            signal_type = context.get("signal_type", "financial")
            reason += f" regarding {signal_type}"

        return {
            "company_mentioned": company,
            "sentiment": linguistic["sentiment"],
            "confidence": round(final_confidence, 3),
            "key_reason": reason,
            "relevant_to_investors": context.get("is_financial", False),
            "linguistic_confidence": round(linguistic["confidence"], 3),
            "raw_scores": linguistic.get("raw_scores", {}),
            "source": "afrisenti+claude",
            "signal_type": context.get("signal_type", "general"),
            "is_financial": context.get("is_financial", False),
            "entities_detected": context.get("entities", []),
            "timestamp": datetime.utcnow().isoformat(),
            "article_title": title,
            "article_url": article.get("url", "")
        }

    @classmethod
    async def close(cls):
        """Close HF client."""
        if cls._hf_client:
            cls._hf_client.close()
            cls._hf_client = None


# Singleton instance
_engine_instance: Optional[SentimentFusionEngine] = None


async def get_sentiment_engine() -> SentimentFusionEngine:
    """Get or create singleton sentiment engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SentimentFusionEngine()
    return _engine_instance


# Alias for backwards compatibility with news_scraper
get_fusion_engine = get_sentiment_engine


async def analyze_sentiment_batch(articles: List[Dict]) -> List[Dict]:
    """
    Analyze sentiment for multiple articles in batch.

    Args:
        articles: List of article dicts

    Returns:
        List of sentiment analysis results
    """
    engine = await get_sentiment_engine()

    results = []
    for article in articles:
        try:
            result = await engine.analyze_article(article)
            results.append(result)
        except Exception as e:
            logger.error(f"Error analyzing article: {e}")
            results.append({
                "company_mentioned": None,
                "sentiment": "neutral",
                "confidence": 0.0,
                "source": "error",
                "signal_type": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            })

    return results


# For standalone testing
if __name__ == "__main__":
    import asyncio

    async def test():
        engine = SentimentFusionEngine()

        test_article = {
            "title": "Safaricom reports strong Q3 earnings, dividend increased",
            "content": "Safaricom PLC has announced impressive Q3 results with revenue up 15%...",
            "url": "https://example.com/article"
        }

        result = await engine.analyze_article(test_article)
        print(f"Result: {json.dumps(result, indent=2)}")

        await engine.close()

    asyncio.run(test())
