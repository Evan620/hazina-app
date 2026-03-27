#!/usr/bin/env python3
"""
Test script for Sentiment Fusion Engine
Tests with real Kenyan financial news headlines
"""

import asyncio
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.sentiment_fusion import get_fusion_engine


# Test articles — real Kenyan financial news headlines
TEST_ARTICLES = [
    {
        "title": "Safaricom M-Pesa merchant numbers grow 20% driven by agency banking push",
        "url": "https://www.businessdailyafrica.com/corporate/technology/safaricom-mpesa-merchant-numbers-grow",
        "source": "Business Daily Africa"
    },
    {
        "title": "KCB Group Q3 profit rises 15% on loan book growth despite rising interest rates",
        "url": "https://www.the-star.co.ke/business/banking/kcb-q3-profit-rises",
        "source": "The Star Kenya"
    },
    {
        "title": "Bamburi Cement profit falls 30% on weak demand and high input costs",
        "url": "https://www.businessdailyafrica.com/markets/manufacturing/bamburi-profit-falls",
        "source": "Business Daily Africa"
    },
    {
        "title": "Kenya Airways passenger numbers rebound as tourism sector recovers",
        "url": "https://www.the-star.co.ke/business/aviation/kenya-airways-passenger-rebound",
        "source": "The Star Kenya"
    },
    {
        "title": "Equity Group regional expansion faces headwinds from currency volatility",
        "url": "https://www.businessdailyafrica.com/markets/banking/equity-regional-headwinds",
        "source": "Business Daily Africa"
    },
    # Swahili / Mixed (Sheng) articles
    {
        "title": "Safaricom imetuma红包 faida kubwa, wateja wamepata mamia ya M-Pesa",
        "url": "https://www.businessdailyafrica.com/corporate/safaricom-mpesa-bonus",
        "source": "Business Daily Africa"
    },
    {
        "title": "KCB yafanya faida kubwa baada ya kukopa gavo serikali",
        "url": "https://www.the-star.co.ke/business/kcb-profits-grow",
        "source": "The Star Kenya"
    },
    {
        "title": "EABL imeshuka baada ya kushuka kodi ya pombe",
        "url": "https://www.businessdailyafrica.com/corporate/eabl-sales-decline",
        "source": "Business Daily Africa"
    },
    {
        "title": "Telkom Kenya inafanya mradi wa fiber mpya mashinani",
        "url": "https://www.businessdailyafrica.com/corporate/telkom-fiber-expansion",
        "source": "Business Daily Africa"
    },
]


async def test_fusion_engine():
    """Test the fusion engine with sample articles."""
    print("=" * 60)
    print("🧪 TESTING SENTIMENT FUSION ENGINE")
    print("=" * 60)
    print()

    engine = get_fusion_engine()

    # Show configuration
    print(f"📊 Configuration:")
    print(f"  • Model: {os.getenv('SENTIMENT_MODEL', 'afrisenti')}")
    print(f"  • Confidence threshold: {os.getenv('SENTIMENT_CONFIDENCE_THRESHOLD', '0.70')}")
    print(f"  • Claude API key: {'✅ Set' if os.getenv('ANTHROPIC_API_KEY') else '❌ Missing'}")
    print()

    results = []

    for i, article in enumerate(TEST_ARTICLES, 1):
        print(f"─" * 60)
        print(f"📰 Article {i}/{len(TEST_ARTICLES)}")
        print(f"─" * 60)
        print(f"Title: {article['title']}")
        print(f"Source: {article['source']}")
        print()

        # Test company detection
        company = engine.detect_company(article['title'])
        print(f"  🏢 Company detected: {company if company else 'None'}")

        if not company:
            print("  ⏭️  Skipped (no NSE company mentioned)")
            print()
            continue

        # Test linguistic sentiment
        print(f"  🌐 Linguistic sentiment: ", end="", flush=True)
        linguistic = await engine.get_linguistic_sentiment(article['title'])
        print(f"{linguistic['sentiment'].upper()} (confidence: {linguistic['confidence']:.2f})")

        # Test financial extraction
        print(f"  💰 Financial context: ", end="", flush=True)
        financial = await engine.extract_financial_context(article['title'], article['source'])
        if financial.get('earnings_mentioned'):
            print("Earnings ✓", end=" ")
        if financial.get('guidance'):
            print(f"Guidance: {financial['guidance']} ✓", end=" ")
        if financial.get('risks'):
            print(f"Risks: {len(financial['risks'])}", end=" ")
        print()

        # Test fusion
        fused = engine.fuse_signals(linguistic, financial, company)
        print(f"  🔀 Fused sentiment: {fused['sentiment'].upper()} (confidence: {fused['confidence']:.2f})")
        print(f"     └─ Linguistic: {fused['linguistic_sentiment']} → Final: {fused['sentiment']}")
        print(f"     └─ Modifier applied: {fused['financial_modifiers']['modifier']:.2f}")

        # Generate explanation
        print(f"  📝 Explanation: ", end="", flush=True)
        explanation = await engine.generate_explanation(fused, financial, article)
        print(f'"{explanation}"')

        # Full result
        result = await engine.analyze_article(article)
        if result:
            results.append(result)
            print()
            print(f"  ✅ Full result:")
            print(f"     • Company: {result['company_mentioned']}")
            print(f"     • Sentiment: {result['sentiment'].upper()}")
            print(f"     • Confidence: {result['confidence']:.2%}")
            print(f"     • Sources: {result['sources']}")
        else:
            print(f"  ❌ Analysis failed")

        print()

    # Summary
    print("=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total articles tested: {len(TEST_ARTICLES)}")
    print(f"Successful analyses: {len(results)}")
    print()

    # Breakdown by sentiment
    from collections import Counter
    sentiments = Counter(r['sentiment'] for r in results)
    for sentiment, count in sentiments.items():
        print(f"  {sentiment.upper()}: {count}")

    print()
    print("✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_fusion_engine())
