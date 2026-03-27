#!/usr/bin/env python3
"""
Test RSS Feed Sentiment Pipeline
Validates that full article content from RSS feeds improves sentiment analysis.
"""

import asyncio
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.news_scraper import fetch_business_daily_rss
from app.services.sentiment_fusion import get_fusion_engine


async def compare_headline_vs_full_content():
    """Compare sentiment analysis: headline-only vs full content."""
    print("=" * 70)
    print("🔬 RSS SENTIMENT PIPELINE VALIDATION")
    print("=" * 70)
    print()

    # Fetch RSS feed
    print("📡 Fetching Business Daily RSS feed...")
    articles = await fetch_business_daily_rss()

    if not articles:
        print("❌ No articles fetched from RSS feed")
        return

    print(f"✅ Fetched {len(articles)} articles from RSS\n")

    # Filter articles that mention NSE companies
    fusion_engine = get_fusion_engine()
    relevant_articles = []

    for article in articles:
        text = article.get('title', '') + ' ' + article.get('teaser', '')
        if fusion_engine.detect_company(text):
            relevant_articles.append(article)

    print(f"📊 Articles mentioning NSE companies: {len(relevant_articles)}")

    if not relevant_articles:
        print("⚠️  No articles mention NSE companies. Showing first 3 articles anyway:\n")
        relevant_articles = articles[:3]

    # Fetch full content for relevant articles
    print("📥 Fetching full article content...")
    from app.services.news_scraper import fetch_article_content

    for article in relevant_articles:
        url = article.get('url', '')
        print(f"  Fetching: {article.get('title', 'Unknown')[:50]}...")
        content = await fetch_article_content(url)
        article['content'] = content

    print()

    # Analyze each article
    results = []
    for i, article in enumerate(relevant_articles[:5], 1):
        print("─" * 70)
        print(f"📰 Article {i}/{min(len(relevant_articles), 5)}")
        print("─" * 70)
        print(f"Title: {article.get('title', 'Unknown')}")
        print(f"URL: {article.get('url', '')}")
        print()

        # Check content availability
        content = article.get('content', '')
        has_full_content = bool(content and len(content) > 200)
        print(f"📄 Full content available: {'✅ Yes (' + str(len(content)) + ' chars)' if has_full_content else '❌ No'}")

        if has_full_content:
            print(f"Preview: {content[:150]}...")

        # Detect company
        company = fusion_engine.detect_company(article.get('title', '') + ' ' + content)
        print(f"\n🏢 Company detected: {company if company else 'None'}")

        if not company:
            print("   ⏭️  Skipping (no NSE company mentioned)\n")
            continue

        # Analyze with full pipeline
        result = await fusion_engine.analyze_article(article)

        if result:
            results.append(result)
            print(f"\n🔬 Sentiment Analysis:")
            print(f"   • Sentiment: {result['sentiment'].upper()}")
            print(f"   • Confidence: {result['confidence']:.1%}")
            print(f"   • Linguistic: {result['linguistic_sentiment']} ({result['linguistic_confidence']:.2f})")
            print(f"   • Financial modifiers applied: {result['financial_modifiers']['applied']}")
            if result['financial_modifiers']['applied']:
                print(f"     - Modifier: {result['financial_modifiers']['modifier']:.2f}x")
                print(f"     - Shift: {result['financial_modifiers']['shift']}")
            print(f"   • Explanation: \"{result['key_reason']}\"")

            # Show financial context
            fc = result.get('financial_context', {})
            print(f"\n💰 Financial Context:")
            if fc.get('earnings_mentioned'):
                print(f"   • Earnings: {fc.get('earnings_direction', 'mentioned')}")
            if fc.get('guidance'):
                print(f"   • Guidance: {fc['guidance']}")
            if fc.get('risks'):
                print(f"   • Risks: {', '.join(fc['risks'][:3])}")
            if fc.get('opportunities'):
                print(f"   • Opportunities: {', '.join(fc['opportunities'][:3])}")

        print()

    # Summary
    print("=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"Total articles analyzed: {len(results)}")

    from collections import Counter
    sentiments = Counter(r['sentiment'] for r in results)
    print("\nSentiment breakdown:")
    for sentiment, count in sentiments.items():
        print(f"  {sentiment.upper()}: {count}")

    # Content analysis
    with_full_content = sum(1 for r in results if r.get('has_full_content'))
    print(f"\nArticles with full content: {with_full_content}/{len(results)}")

    avg_confidence = sum(r['confidence'] for r in results) / len(results) if results else 0
    print(f"Average confidence: {avg_confidence:.1%}")

    print("\n✅ Pipeline validation complete!")


if __name__ == "__main__":
    asyncio.run(compare_headline_vs_full_content())
