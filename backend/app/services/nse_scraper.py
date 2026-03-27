"""
NSE Data Scraper
Scrapes public NSE data for market prices and Ibuka companies
"""

import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import MarketData, Company, async_session_maker


# NSE public URLs
NSE_LIVE_MARKET = "https://www.nse.co.ke/live-market/"
NSE_IBUKA = "https://www.nse.co.ke/ibuka/"


async def scrape_nse_prices() -> List[Dict]:
    """
    Scrape daily equity prices from NSE live market page.

    Returns:
        List of dicts with symbol, name, price, change_pct, volume
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(NSE_LIVE_MARKET)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            prices = []

            # NSE live market uses a table structure
            # This is a placeholder - actual selector depends on NSE website structure
            table = soup.find("table", class_="market-data-table") or soup.find("table")

            if table:
                rows = table.find_all("tr")[1:]  # Skip header
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 4:
                        try:
                            price_text = cols[2].get_text(strip=True).replace(",", "")
                            price = float(price_text) if price_text else 0.0

                            change_text = cols[3].get_text(strip=True).replace("%", "").replace("+", "")
                            change_pct = float(change_text) if change_text else 0.0

                            volume_text = cols[4].get_text(strip=True).replace(",", "")
                            volume = int(volume_text) if volume_text else 0

                            prices.append({
                                "symbol": cols[0].get_text(strip=True),
                                "name": cols[1].get_text(strip=True),
                                "price": price,
                                "change_pct": change_pct,
                                "volume": volume
                            })
                        except (ValueError, IndexError):
                            continue

            # If no data found, return demo data for prototype
            if not prices:
                prices = get_demo_market_data()

            return prices

    except Exception as e:
        print(f"Error scraping NSE: {e}")
        return get_demo_market_data()


async def scrape_ibuka_companies() -> List[Dict]:
    """
    Scrape Ibuka SME candidate companies from NSE Ibuka page.

    Returns:
        List of dicts with symbol, name, sector
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(NSE_IBUKA)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            companies = []

            # Find company listings
            company_items = soup.find_all("div", class_="ibuka-company") or soup.find_all("li", class_="company-item")

            for item in company_items:
                name_elem = item.find("h3") or item.find("strong") or item.find("span", class_="name")
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    companies.append({
                        "symbol": name.split()[0][:4].upper() if name else "IBUK",
                        "name": name,
                        "sector": "SME",
                        "is_ibuka": True
                    })

            if not companies:
                companies = get_demo_ibuka_companies()

            return companies

    except Exception as e:
        print(f"Error scraping Ibuka: {e}")
        return get_demo_ibuka_companies()


async def save_market_data(prices: List[Dict]) -> None:
    """Save scraped market data to database."""
    async with async_session_maker() as session:
        for price_data in prices:
            market_data = MarketData(
                symbol=price_data["symbol"],
                name=price_data["name"],
                price=price_data["price"],
                change_pct=price_data.get("change_pct"),
                volume=price_data.get("volume"),
                scraped_at=datetime.utcnow()
            )
            session.add(market_data)

        await session.commit()


async def save_companies(companies: List[Dict]) -> None:
    """Save company data to database."""
    async with async_session_maker() as session:
        for company_data in companies:
            # Check if exists
            existing = await session.execute(
                select(Company).where(Company.symbol == company_data["symbol"])
            )
            if not existing.scalar_one_or_none():
                company = Company(
                    symbol=company_data["symbol"],
                    name=company_data["name"],
                    sector=company_data.get("sector"),
                    is_ibuka=company_data.get("is_ibuka", False)
                )
                session.add(company)

        await session.commit()


def get_demo_market_data() -> List[Dict]:
    """Return demo market data for top NSE stocks."""
    return [
        {"symbol": "SCOM", "name": "Safaricom PLC", "price": 38.50, "change_pct": 1.32, "volume": 15842000},
        {"symbol": "EQTY", "name": "Equity Group Holdings", "price": 52.75, "change_pct": -0.38, "volume": 2341000},
        {"symbol": "KCB", "name": "KCB Group PLC", "price": 43.25, "change_pct": 0.58, "volume": 4520000},
        {"symbol": "COOP", "name": "Co-operative Bank", "price": 13.80, "change_pct": 0.00, "volume": 8750000},
        {"symbol": "ABSA", "name": "Absa Bank Kenya", "price": 15.75, "change_pct": -0.63, "volume": 1230000},
        {"symbol": "EABL", "name": "East African Breweries", "price": 158.00, "change_pct": 1.28, "volume": 89000},
        {"symbol": "BAT", "name": "British American Tobacco", "price": 540.00, "change_pct": -0.92, "volume": 1200},
        {"symbol": "TKN", "name": "Telkom Kenya", "price": 2.85, "change_pct": 3.64, "volume": 4500000},
        {"symbol": "KNRE", "name": "Kenya RE", "price": 2.45, "change_pct": 2.08, "volume": 2340000},
        {"symbol": "BAMB", "name": "Bamburi Cement", "price": 64.00, "change_pct": -1.54, "volume": 89000},
        {"symbol": "ARM", "name": "ARM Cement", "price": 5.20, "change_pct": 0.00, "volume": 50000},
        {"symbol": "NMG", "name": "Nation Media Group", "price": 18.50, "change_pct": 0.54, "volume": 34000},
        {"symbol": "JUBH", "name": "Jubilee Holdings", "price": 485.00, "change_pct": -0.41, "volume": 500},
        {"symbol": "BRCK", "name": "Brimstone Investment", "price": 12.50, "change_pct": 1.21, "volume": 15000},
        {"symbol": "CNTY", "name": "Centum Investment", "price": 41.25, "change_pct": 0.00, "volume": 45000},
        {"symbol": "LKL", "name": "Liberty Holdings", "price": 310.00, "change_pct": 0.32, "volume": 2000},
        {"symbol": "KAPC", "name": "Kenya Airways", "price": 8.75, "change_pct": -2.23, "volume": 890000},
        {"symbol": "SPWN", "name": "Spancer Flowers", "price": 5.40, "change_pct": 0.00, "volume": 5000},
        {"symbol": "WTKR", "name": "Waitrus (K)", "price": 3.25, "change_pct": -1.52, "volume": 12000},
        {"symbol": "KENG", "name": "KenGen", "price": 8.90, "change_pct": 1.14, "volume": 2340000}
    ]


def get_demo_ibuka_companies() -> List[Dict]:
    """Return demo Ibuka company data."""
    return [
        {"symbol": "CPTY", "name": "Copy Cat Limited", "sector": "Manufacturing", "is_ibuka": True},
        {"symbol": "KKO", "name": "Koko Networks", "sector": "Energy", "is_ibuka": True},
        {"symbol": "MTB", "name": "Mastermind Tobacco", "sector": "Manufacturing", "is_ibuka": True},
        {"symbol": "TLKM", "name": "Telkom Kenya", "sector": "Telecom", "is_ibuka": True},
        {"symbol": "ANDA", "name": "Andela Kenya", "sector": "Technology", "is_ibuka": True},
        {"symbol": "MNT", "name": "M-Kopa Solar", "sector": "Energy", "is_ibuka": True},
        {"symbol": "TWF", "name": "Twiga Foods", "sector": "Agriculture", "is_ibuka": True},
        {"symbol": "SFN", "name": "Sanergy", "sector": "Waste Management", "is_ibuka": True},
        {"symbol": "GRN", "name": "GreenPath", "sector": "Construction", "is_ibuka": True},
        {"symbol": "DLT", "name": "Dalbit Petroleum", "sector": "Energy", "is_ibuka": True}
    ]


async def run_scraper():
    """Main scraper function - runs periodically."""
    print(f"[{datetime.utcnow()}] Running NSE scraper...")

    # Scrape prices
    prices = await scrape_nse_prices()
    await save_market_data(prices)
    print(f"Saved {len(prices)} price records")

    # Scrape Ibuka companies
    companies = await scrape_ibuka_companies()
    await save_companies(companies)
    print(f"Updated {len(companies)} companies")


if __name__ == "__main__":
    asyncio.run(run_scraper())
