"""
Seed database with demo data for Hazina prototype
"""

import asyncio
from datetime import datetime, timedelta
from app.db.database import engine, Company, MarketData, SentimentSignal
from sqlalchemy.ext.asyncio import AsyncSession


async def seed_companies():
    """Seed NSE and Ibuka companies."""
    from sqlalchemy import select

    nse_companies = [
        ("SCOM", "Safaricom PLC", "Telecommunications", False),
        ("EQTY", "Equity Group Holdings", "Banking", False),
        ("KCB", "KCB Group PLC", "Banking", False),
        ("COOP", "Co-operative Bank", "Banking", False),
        ("ABSA", "Absa Bank Kenya", "Banking", False),
        ("EABL", "East African Breweries", "Manufacturing", False),
        ("BAT", "British American Tobacco", "Manufacturing", False),
        ("TKN", "Telkom Kenya", "Telecommunications", False),
        ("BAMB", "Bamburi Cement", "Manufacturing", False),
        ("ARM", "ARM Cement", "Manufacturing", False),
        ("NMG", "Nation Media Group", "Media", False),
        ("JUBH", "Jubilee Holdings", "Insurance", False),
        ("CNTY", "Centum Investment", "Investment", False),
        ("KAPC", "Kenya Airways", "Aviation", False),
        ("KENG", "Kenya Electricity Generating", "Energy", False),
        ("KNRE", "Kenya Reinsurance", "Insurance", False),
        ("BRCK", "Brimstone Investment", "Investment", False),
        ("LKL", "Liberty Holdings", "Insurance", False),
        ("SPWN", "Spencer Flowers", "Agriculture", False),
        ("WTKR", "Walters Kenya", "Investment", False),
    ]

    ibuka_companies = [
        ("CPTY", "Copy Cat Limited", "Manufacturing", True),
        ("KKO", "Koko Networks", "Energy", True),
        ("MTB", "Mastermind Tobacco", "Manufacturing", True),
        ("ANDA", "Andela Kenya", "Technology", True),
        ("MNT", "M-Kopa Solar", "Energy", True),
        ("TWF", "Twiga Foods", "Agriculture", True),
        ("SFN", "Sanergy", "Waste Management", True),
        ("GRN", "GreenPath Technologies", "Construction", True),
        ("DLT", "Dalbit Petroleum", "Energy", True),
        ("LZ", "LazyEye", "Technology", True),
    ]

    all_companies = nse_companies + ibuka_companies

    async with AsyncSession(engine) as session:
        for symbol, name, sector, is_ibuka in all_companies:
            # Check if exists
            result = await session.execute(
                select(Company).where(Company.symbol == symbol)
            )
            if not result.scalar_one_or_none():
                company = Company(
                    symbol=symbol,
                    name=name,
                    sector=sector,
                    is_ibuka=is_ibuka
                )
                session.add(company)

        await session.commit()
        print(f"✅ Seeded {len(all_companies)} companies")


async def seed_market_data():
    """Seed demo market data."""
    import random

    prices = [
        ("SCOM", "Safaricom PLC", 38.50, 1.32, 15842000),
        ("EQTY", "Equity Group", 52.75, -0.38, 2341000),
        ("KCB", "KCB Group", 43.25, 0.58, 4520000),
        ("COOP", "Co-operative Bank", 13.80, 0.00, 8750000),
        ("ABSA", "Absa Bank", 15.75, -0.63, 1230000),
        ("EABL", "East African Breweries", 158.00, 1.28, 89000),
        ("BAT", "British American Tobacco", 540.00, -0.92, 1200),
        ("TKN", "Telkom Kenya", 2.85, 3.64, 4500000),
        ("BAMB", "Bamburi Cement", 64.00, -1.54, 89000),
        ("ARM", "ARM Cement", 5.20, 0.00, 50000),
        ("NMG", "Nation Media", 18.50, 0.54, 34000),
        ("JUBH", "Jubilee Holdings", 485.00, -0.41, 500),
        ("CNTY", "Centum Investment", 41.25, 0.00, 45000),
        ("LKL", "Liberty Holdings", 310.00, 0.32, 2000),
        ("KAPC", "Kenya Airways", 8.75, -2.23, 890000),
        ("SPWN", "Spencer Flowers", 5.40, 0.00, 5000),
        ("WTKR", "Walters Kenya", 3.25, -1.52, 12000),
        ("KENG", "Kenya Gen", 8.90, 1.14, 2340000),
        ("KNRE", "Kenya Re", 2.45, 2.08, 2340000),
        ("BRCK", "Brimstone Investment", 12.50, 1.21, 15000),
    ]

    async with AsyncSession(engine) as session:
        for symbol, name, price, change_pct, volume in prices:
            # Add multiple data points over past week
            for i in range(7):
                # Add slight random variation
                variaton = random.uniform(-0.5, 0.5)
                timestamp = datetime.utcnow() - timedelta(days=6-i, hours=random.randint(0, 23))

                market_data = MarketData(
                    symbol=symbol,
                    name=name,
                    price=round(price + variaton, 2),
                    change_pct=round(change_pct + random.uniform(-0.2, 0.2), 2),
                    volume=volume + random.randint(-500000, 500000),
                    scraped_at=timestamp
                )
                session.add(market_data)

        await session.commit()
        print(f"✅ Seeded {len(prices) * 7} market data points")


async def seed_sentiment_signals():
    """Seed demo sentiment signals."""
    signals = [
        ("SCOM", "positive", 0.85, "Strong M-Pesa growth driven by new merchant onboarding", "Business Daily Africa"),
        ("EQTY", "neutral", 0.72, "Regional expansion on track but margin pressure from rising rates", "Business Daily Africa"),
        ("KCB", "positive", 0.78, "Q3 earnings beat expectations on loan book growth", "The Star Kenya"),
        ("BAMB", "negative", 0.88, "Housing slowdown and rising input costs pressure margins", "Business Daily Africa"),
        ("EABL", "neutral", 0.65, "Volumes stable but excise duty increase weighing on profitability", "Business Daily Africa"),
        ("KAPC", "positive", 0.70, "Tourism recovery driving passenger numbers up", "The Star Kenya"),
    ]

    async with AsyncSession(engine) as session:
        for company_mentioned, sentiment, confidence, reason, source in signals:
            # Add multiple signals over past 48 hours
            for i in range(3):
                timestamp = datetime.utcnow() - timedelta(hours=6 + i*8)

                signal = SentimentSignal(
                    company_mentioned=company_mentioned,
                    sentiment=sentiment,
                    confidence=round(confidence - 0.05*i, 2),
                    key_reason=reason,
                    relevant_to_investors=True,
                    article_url=f"https://example.com/article/{i}",
                    article_title=f"Analysis: {company_mentioned} market update",
                    source=source,
                    created_at=timestamp
                )
                session.add(signal)

        await session.commit()
        print(f"✅ Seeded {len(signals) * 3} sentiment signals")


async def main():
    """Run all seed functions."""
    print("🌱 Seeding Hazina database...")
    await seed_companies()
    await seed_market_data()
    await seed_sentiment_signals()
    print("✅ Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(main())
