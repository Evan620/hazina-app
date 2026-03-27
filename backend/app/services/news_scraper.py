"""
News Scraper & Sentiment Engine
Sources:
- Business Daily Africa (RSS + Playwright for full content) ✅
- The Star Kenya (BeautifulSoup) ✅
- Reuters Africa (TODO: blocked 401, requires Playwright)
- Citizen TV Kenya (TODO: returning 500 errors)

For demo, Business Daily + The Star provide sufficient NSE coverage.
"""

import asyncio
import httpx
import feedparser
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from playwright.async_api import async_playwright

from app.db.database import SentimentSignal, async_session_maker
from app.services.sentiment_fusion import get_fusion_engine, NSE_SYMBOLS


# ============================================================================
# CONFIGURATION
# ============================================================================

# RSS Feed URLs
BUSINESS_DAILY_RSS = "https://www.businessdailyafrica.com/bd/rss.xml"
REUTERS_RSS = "https://reutersagency.com/rssFeed/marketsNews?channelId=RSSSYNCRONISE"
REUTERS_AFRICA_RSS = "https://www.reuters.com/finance/markets-africa"  # Alternative: use Reuters main feed

# Cache for article content
_content_cache: Dict[str, str] = {}


# ============================================================================
# BUSINESS DAILY (RSS + Playwright)
# ============================================================================

async def fetch_business_daily_rss() -> List[Dict]:
    """Fetch articles from Business Daily RSS feed."""
    articles = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(BUSINESS_DAILY_RSS)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            for entry in feed.entries[:30]:
                teaser = entry.get('summary', '') or entry.get('description', '')
                if '<' in teaser and '>' in teaser:
                    soup_teaser = BeautifulSoup(teaser, 'html.parser')
                    teaser = soup_teaser.get_text(separator=' ', strip=True)

                articles.append({
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'source': 'Business Daily Africa',
                    'content': '',
                    'teaser': teaser,
                    'published': entry.get('published', None)
                })

            print(f"[RSS] Business Daily: {len(articles)} articles")

    except Exception as e:
        print(f"Error fetching Business Daily RSS: {e}")

    return articles


async def fetch_business_daily_content_playwright(url: str) -> str:
    """Fetch full article content from Business Daily using Playwright."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.goto(url, wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)  # Wait for JS rendering

            # Extract paragraphs
            paragraphs = await page.locator('p').all_text_contents()

            # Filter meaningful content
            content_parts = []
            for p in paragraphs:
                text = p.strip()
                if len(text) > 50 and not any(skip in text.lower() for skip in [
                    'subscribe', 'premium content', 'sign in', 'home', 'corporate',
                    'markets & finance', 'privacy policy', 'terms'
                ]):
                    content_parts.append(text)

            await browser.close()

            content = ' '.join(content_parts)
            if len(content) > 500:
                return content

            return ""

    except Exception as e:
        print(f"Error fetching Business Daily content with Playwright: {e}")
        return ""


# ============================================================================
# REUTERS AFRICA (RSS)
# ============================================================================

async def fetch_reuters_rss() -> List[Dict]:
    """
    Fetch articles from Reuters Africa RSS.
    NOTE: Currently blocked (401), would need Playwright.
    """
    # TODO: Implement with Playwright when needed
    print("[RSS] Reuters Africa: Skipped (blocked 401, requires Playwright)")
    return []


async def fetch_reuters_content(url: str) -> str:
    """Fetch full article content from Reuters."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Reuters uses specific article body class
            selectors = [
                '.article-body p',
                '.StandardArticleBodyBody p',
                'article p',
                '[data-testid="article-body"] p'
            ]

            for selector in selectors:
                elems = soup.select(selector)
                if elems:
                    paragraphs = [p.get_text(strip=True) for p in elems]
                    content = ' '.join([p for p in paragraphs if len(p) > 30])
                    if len(content) > 300:
                        return content

            return ""

    except Exception as e:
        print(f"Error fetching Reuters content: {e}")
        return ""


# ============================================================================
# CITIZEN TV KENYA
# ============================================================================

async def scrape_citizen() -> List[Dict]:
    """
    Scrape business articles from Citizen TV Kenya.
    NOTE: Currently returning 500 errors.
    """
    # TODO: Fix URL or use Playwright
    print("[Citizen] Skipped (site returning 500 errors)")
    return []


async def fetch_citizen_content(url: str) -> str:
    """Fetch full article content from Citizen Digital."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Citizen content is in entry-content
            content_div = soup.find("div", class_="entry-content")
            if content_div:
                paragraphs = content_div.find_all("p")
                content = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
                if len(content) > 300:
                    return content

            return ""

    except Exception as e:
        print(f"Error fetching Citizen content: {e}")
        return ""


# ============================================================================
# THE STAR KENYA (BeautifulSoup - Working)
# ============================================================================

async def scrape_the_star() -> List[Dict]:
    """Scrape headlines from The Star Kenya business section."""
    articles = []

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get("https://www.the-star.co.ke/business")
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            for article_tag in soup.find_all("article", limit=15):
                title_elem = article_tag.find("h2") or article_tag.find("h3")
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = article_tag.find("a", href=True)
                    if link:
                        url = link.get("href", "")
                        if not url.startswith("http"):
                            url = "https://www.the-star.co.ke" + url

                        desc_elem = article_tag.find("p")
                        description = desc_elem.get_text(strip=True) if desc_elem else ""

                        articles.append({
                            "title": title,
                            "url": url,
                            "source": "The Star Kenya",
                            "content": "",
                            "teaser": description
                        })

            print(f"[The Star] Found {len(articles)} articles")

    except Exception as e:
        print(f"Error scraping The Star: {e}")

    return articles


async def fetch_the_star_content(url: str) -> str:
    """Fetch full article content from The Star Kenya."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        async with httpx.AsyncClient(timeout=15.0, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")

            content_parts = []
            for p in paragraphs:
                text = p.get_text(strip=True)
                if len(text) > 30 and not any(skip in text.lower() for skip in
                    ['subscribe', 'newsletter', 'follow us', 'share this']):
                    content_parts.append(text)

            content = " ".join(content_parts)
            if len(content) > 500:
                return content

            return ""

    except Exception as e:
        print(f"Error fetching The Star content: {e}")
        return ""


# ============================================================================
# CONTENT FETCHER (Router)
# ============================================================================

async def fetch_article_content(url: str) -> str:
    """Fetch full article content from URL based on domain."""
    if url in _content_cache:
        return _content_cache[url]

    content = ""

    if "businessdailyafrica.com" in url:
        content = await fetch_business_daily_content_playwright(url)
    elif "reuters.com" in url:
        content = await fetch_reuters_content(url)
    elif "the-star.co.ke" in url:
        content = await fetch_the_star_content(url)
    elif "citizen.digital" in url:
        content = await fetch_citizen_content(url)

    if content:
        _content_cache[url] = content

    return content


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

async def run_news_scraper():
    """Main news scraper - fetches from working sources."""
    print(f"[{datetime.utcnow()}] Running news scraper...")
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

    # Filter for NSE companies
    print("🔍 Filtering for NSE companies...")
    nse_articles = []

    for article in all_articles:
        text = article.get('title', '') + ' ' + article.get('teaser', '')
        for symbol, name in NSE_SYMBOLS.items():
            if symbol.upper() in text.upper() or name.upper() in text.upper():
                article['company'] = symbol
                nse_articles.append(article)
                break

    print(f"   Articles mentioning NSE companies: {len(nse_articles)}")

    # Fetch full content for NSE articles
    print("📥 Fetching full article content...")

    for article in nse_articles:
        url = article.get('url', '')
        print(f"   {article.get('company', 'Unknown')}: {article.get('title', 'Unknown')[:40]}...")
        content = await fetch_article_content(url)
        article['content'] = content

    with_content = sum(1 for a in nse_articles if a.get('content') and len(a.get('content', '')) > 300)
    print(f"   Articles with full content: {with_content}/{len(nse_articles)}")

    # Analyze sentiment
    print("\n🧠 Running sentiment fusion analysis...")
    signals = []

    fusion_engine = await get_fusion_engine()
    for article in nse_articles:
        result = await fusion_engine.analyze_article(article)
        # Only save signals where a company was detected
        if result and result.get('company_mentioned'):
            signals.append(result)
            print(f"   {result.get('company_mentioned', 'Unknown')}: {result.get('sentiment', 'unknown').upper()} ({result.get('confidence', 0):.0%})")

    print(f"\n✅ Generated {len(signals)} sentiment signals")

    # Save to database
    await save_sentiment_signals(signals)

    return signals


async def analyze_article_sentiment(article: Dict) -> Optional[Dict]:
    """Analyze a single article using fusion engine."""
    try:
        fusion_engine = await get_fusion_engine()
        return await fusion_engine.analyze_article(article)
    except Exception as e:
        print(f"Error analyzing article: {e}")
        return None


async def save_sentiment_signals(signals: List[Dict]) -> None:
    """Save sentiment signals to database."""
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
                source=signal_data.get("source", ""),
                created_at=created_at
            )
            session.add(signal)

        await session.commit()


def get_demo_sentiment_signals() -> List[Dict]:
    """Return demo sentiment signals for testing."""
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
            "confidence": 0.65,
            "key_reason": "Consumer finance unit posts revenue growth",
            "relevant_to_investors": True,
            "article_url": "https://www.businessdailyafrica.com/",
            "article_title": "Absa consumer finance unit posts growth",
            "source": "Business Daily Africa",
            "created_at": (datetime.utcnow() - timedelta(hours=8)).isoformat()
        },
    ]


if __name__ == "__main__":
    asyncio.run(run_news_scraper())
