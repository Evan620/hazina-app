"""
Verification Service - Cross-checks company-provided data against public sources.
Confirms claimed data, finds discrepancies, and flags compliance issues.
"""

import httpx
import re
import logging
from typing import Dict, List, Optional
from playwright.async_api import async_playwright

from app.services.news_scraper import fetch_business_daily_rss, scrape_the_star

logger = logging.getLogger(__name__)


# Compliance keywords that indicate potential issues
COMPLIANCE_KEYWORDS = ["fine", "penalty", "lawsuit", "tax", "court", "fraud", "scandal", "investigation", "regulator", "default", "bankruptcy"]


async def cross_check_company_data(
    company_name: str,
    company_input: Dict
) -> Dict:
    """
    Verify company claims against public sources.

    Args:
        company_name: Name of company
        company_input: {
            "name": str,
            "sector": str,
            "website": str,
            "revenue_history": {year: float, ...},
            "board_members": [{"name": str, "role": str, "independent": bool}, ...],
            "tax_compliant": bool,
            "licenses": List[str],
            "litigation": str,
        }

    Returns:
        {
            "confirmations": [
                {"field": "revenue", "value": "KES 2.5B", "verified_by": "...", "source": "..."}
            ],
            "discrepancies": [
                {"field": "revenue", "claimed": "KES 3B", "public": "KES 2.5B", "severity": "high"}
            ],
            "red_flags": [
                {"field": "compliance", "issue": "KRA tax dispute", "source": "...", "severity": "medium"}
            ],
            "trust_score": 0.75,
            "sources_used": ["News articles", "Company website", "Public records"]
        }
    """
    confirmations = []
    discrepancies = []
    red_flags = []
    sources_used = []

    # 1. Search news articles for company mentions
    logger.info(f"Searching news for {company_name}...")
    news_articles = await search_news_articles(company_name)
    sources_used.append("News articles")

    # 2. Verify revenue against news mentions
    if company_input.get("revenue_history"):
        latest_year = max(company_input["revenue_history"].keys()) if company_input["revenue_history"] else None
        if latest_year:
            claimed_revenue = company_input["revenue_history"][latest_year]
            public_revenue = extract_revenue_from_news(news_articles)

            if public_revenue:
                if abs(public_revenue - claimed_revenue) > 0.15 * claimed_revenue:
                    discrepancies.append({
                        "field": "revenue",
                        "claimed": f"KES {claimed_revenue/1e9:.1f}B" if claimed_revenue >= 1e9 else f"KES {claimed_revenue/1e6:.0f}M",
                        "public": f"KES {public_revenue/1e9:.1f}B" if public_revenue >= 1e9 else f"KES {public_revenue/1e6:.0f}M",
                        "source": "News articles",
                        "severity": "high"
                    })
                else:
                    confirmations.append({
                        "field": "revenue",
                        "value": f"KES {claimed_revenue/1e9:.1f}B" if claimed_revenue >= 1e9 else f"KES {claimed_revenue/1e6:.0f}M",
                        "verified_by": "News articles",
                        "source": "Business Daily Africa / The Star Kenya"
                    })

    # 3. Check news for compliance red flags
    for article in news_articles:
        title_lower = article.get("title", "").lower()
        teaser_lower = article.get("teaser", "").lower()

        for keyword in COMPLIANCE_KEYWORDS:
            if keyword in title_lower or keyword in teaser_lower:
                # Check if this is actually about the company
                company_lower = company_name.lower()
                if company_lower in title_lower or company_lower in teaser_lower:
                    red_flags.append({
                        "field": "compliance",
                        "issue": article.get("title", f"Compliance concern: {keyword}"),
                        "source": article.get("source", "News"),
                        "url": article.get("url", ""),
                        "severity": "medium" if keyword in ["tax", "fine", "penalty"] else "low"
                    })
                    break

    # 4. Scrape company website for verification
    if company_input.get("website"):
        logger.info(f"Scraping website: {company_input['website']}")
        website_data = await scrape_company_website(company_input["website"])
        sources_used.append("Company website")

        # Verify company is active
        if website_data.get("text"):
            confirmations.append({
                "field": "website",
                "value": company_input["website"],
                "verified_by": "Website accessible",
                "source": company_input["website"]
            })

        # Check for employee count mentions
        employee_count = extract_employee_count(website_data.get("text", ""))
        if employee_count:
            confirmations.append({
                "field": "employees",
                "value": f"~{employee_count} employees",
                "verified_by": "Company website",
                "source": company_input["website"]
            })

    # 5. Verify board members (basic check - at least some are listed)
    # NOTE: No fake discrepancies - governance score handles NSE requirements
    if company_input.get("board_members"):
        board_count = len([b for b in company_input["board_members"] if b.get("name")])
        if board_count > 0:
            confirmations.append({
                "field": "board",
                "value": f"{board_count} board member{'s' if board_count != 1 else ''} declared",
                "verified_by": "Company input",
                "source": "Self-reported"
            })

    # 6. Verify tax compliance claim
    if company_input.get("tax_compliant"):
        # Check if any red flags contradict this
        tax_flags = [f for f in red_flags if "tax" in f.get("issue", "").lower()]
        if tax_flags:
            discrepancies.append({
                "field": "compliance",
                "claimed": "Tax compliant",
                "public": "Tax issues found in news",
                "source": "News articles",
                "severity": "high"
            })

    # Calculate trust score
    trust_score = calculate_trust_score(confirmations, discrepancies, red_flags)

    logger.info(f"Verification complete: {len(confirmations)} confirmations, {len(discrepancies)} discrepancies, {len(red_flags)} red flags")

    return {
        "confirmations": confirmations,
        "discrepancies": discrepancies,
        "red_flags": red_flags,
        "trust_score": trust_score,
        "sources_used": list(set(sources_used))
    }


async def search_news_articles(company_name: str) -> List[Dict]:
    """
    Search news articles for company mentions.

    Returns articles from Business Daily and The Star that mention the company.
    """
    all_articles = []

    # Fetch from existing scrapers
    try:
        bd_articles = await fetch_business_daily_rss()
        all_articles.extend(bd_articles)
    except Exception as e:
        logger.warning(f"Failed to fetch Business Daily articles: {e}")

    try:
        star_articles = await scrape_the_star()
        all_articles.extend(star_articles)
    except Exception as e:
        logger.warning(f"Failed to fetch The Star articles: {e}")

    # Filter for company mentions
    company_lower = company_name.lower()
    # Also check for common variations
    variations = [company_lower]
    if "limited" in company_lower:
        variations.append(company_lower.replace("limited", "ltd"))
    if "ltd" in company_lower:
        variations.append(company_lower.replace("ltd", "limited"))

    matching = []
    for article in all_articles:
        title = article.get("title", "").lower()
        teaser = article.get("teaser", "").lower()
        for variation in variations:
            if variation in title or variation in teaser:
                matching.append(article)
                break

    return matching


def extract_revenue_from_news(articles: List[Dict]) -> Optional[float]:
    """
    Extract revenue figures from news articles.

    Looks for patterns like:
    - "KES 2.5 billion"
    - "KES 2.5B"
    - "2.5 billion shillings"
    """
    for article in articles:
        text = article.get("title", "") + " " + article.get("teaser", "")

        # Pattern 1: KES X billion / KES XB
        matches = re.findall(r'KES\s*([\d.]+)\s*(?:billion|B|b)\b', text, re.IGNORECASE)
        if matches:
            return float(matches[0]) * 1_000_000_000

        # Pattern 2: X billion shillings
        matches = re.findall(r'([\d.]+)\s*billion\s*shillings', text, re.IGNORECASE)
        if matches:
            return float(matches[0]) * 1_000_000_000

        # Pattern 3: KES X million / KES XM
        matches = re.findall(r'KES\s*([\d.]+)\s*(?:million|M|m)\b', text, re.IGNORECASE)
        if matches:
            return float(matches[0]) * 1_000_000

        # Pattern 4: X million shillings
        matches = re.findall(r'([\d.]+)\s*million\s*shillings', text, re.IGNORECASE)
        if matches:
            return float(matches[0]) * 1_000_000

    return None


async def scrape_company_website(website_url: str) -> Dict:
    """
    Extract publicly available information from company website.

    Returns page text and basic metadata.
    """
    if not website_url:
        return {}

    # Ensure URL has protocol
    if not website_url.startswith("http"):
        website_url = "https://" + website_url

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            await page.goto(website_url, wait_until='domcontentloaded', timeout=15000)
            await page.wait_for_timeout(2000)

            # Get page text
            text = await page.locator('body').text_content()

            await browser.close()

            return {
                "text": text[:10000] if text else "",  # First 10,000 chars
                "accessible": True
            }

    except Exception as e:
        logger.warning(f"Failed to scrape website {website_url}: {e}")
        return {"text": "", "accessible": False, "error": str(e)}


def extract_employee_count(text: str) -> Optional[int]:
    """
    Extract employee count from website text.

    Looks for patterns like "500 employees", "staff of 500", etc.
    """
    patterns = [
        r'(\d+)\s*employees?',
        r'(\d+)\s*staff',
        r'(\d+)\s*workers?',
        r'team\s*of\s*(\d+)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            return int(matches[0])

    return None


def calculate_trust_score(
    confirmations: List,
    discrepancies: List,
    red_flags: List
) -> float:
    """
    Calculate overall trust score (0-1).

    Base score: 0.5
    +0.1 for each confirmation
    -0.15 for each discrepancy
    -0.1 for each red flag
    """
    score = 0.5

    score += len(confirmations) * 0.1
    score -= len(discrepancies) * 0.15
    score -= len(red_flags) * 0.1

    return max(0.0, min(1.0, score))


# Demo verification data for testing
DEMO_VERIFICATION = {
    "Copy Cat Limited": {
        "confirmations": [
            {"field": "revenue", "value": "KES 2.5B", "verified_by": "News articles", "source": "Business Daily Africa"},
            {"field": "website", "value": "https://ccopy.co.ke", "verified_by": "Website accessible", "source": "Company website"},
            {"field": "employees", "value": "~500 employees", "verified_by": "Company website", "source": "ccopy.co.ke"},
        ],
        "discrepancies": [],
        "red_flags": [
            {"field": "compliance", "issue": "Historical KRA tax dispute (resolved)", "source": "Public records", "severity": "low"}
        ],
        "trust_score": 0.82,
        "sources_used": ["News articles", "Company website"]
    },
    "Koko Networks": {
        "confirmations": [
            {"field": "revenue", "value": "Growing rapidly", "verified_by": "News articles", "source": "Multiple sources"},
            {"field": "website", "value": "https://koko-networks.com", "verified_by": "Website accessible", "source": "Company website"},
        ],
        "discrepancies": [],
        "red_flags": [],
        "trust_score": 0.90,
        "sources_used": ["News articles", "Company website", "TechCrunch"]
    }
}


async def get_demo_verification(company_name: str) -> Optional[Dict]:
    """Get demo verification data for testing."""
    for key, data in DEMO_VERIFICATION.items():
        if company_name.lower() in key.lower() or key.lower() in company_name.lower():
            return data
    return None
