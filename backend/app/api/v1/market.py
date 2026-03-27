"""
Market data endpoints
NSE live market data, prices, and company information
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
from typing import List, Optional
import logging

from app.db.database import get_db, MarketData, Company
from app.services.nse_prices import fetch_nse_prices, get_price, format_price, format_change, get_demo_prices

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/prices")
async def get_market_prices(
    refresh: bool = False,
    symbols: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get current NSE stock prices (live from deveintapps API).

    Args:
        refresh: Force cache refresh (default: false)
        symbols: Comma-separated list of symbols to filter (e.g., "SCOM,EQTY,KCB")

    Returns:
        List of stock prices with change data:
        [{
            "symbol": "SCOM",
            "name": "Safaricom PLC",
            "price": 27.95,
            "prev_price": 27.95,
            "change": 0.50,
            "change_percent": 1.32,
            "today_open": 28.00,
            "today_high": 29.00,
            "today_low": 27.90,
            "volume": 3453330,
            "formatted_price": "KES 27.95",
            "formatted_change": "+1.32%"
        }, ...]
    """
    try:
        # Fetch live prices from NSE API
        prices = await fetch_nse_prices()

        if not prices:
            logger.warning("No prices from API, using demo data")
            prices = get_demo_prices()

        # Add company names and formatted strings
        for p in prices:
            p["name"] = get_company_name(p["symbol"])
            p["formatted_price"] = format_price(p["price"])
            p["formatted_change"] = format_change(p["change"], p["change_percent"])

        # Filter by symbols if provided
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            prices = [p for p in prices if p["symbol"] in symbol_list]

        return {
            "prices": prices,
            "count": len(prices),
            "source": "NSE (via deveintapps)",
            "last_updated": prices[0]["last_updated"] if prices else None
        }

    except Exception as e:
        logger.error(f"Error fetching market prices: {e}")
        # Return demo data on error
        prices = get_demo_prices()
        for p in prices:
            p["name"] = get_company_name(p["symbol"])
            p["formatted_price"] = format_price(p["price"])
            p["formatted_change"] = format_change(p["change"], p["change_percent"])

        return {
            "prices": prices,
            "count": len(prices),
            "source": "Demo data (API unavailable)",
            "error": str(e)
        }


@router.get("/prices/{symbol}")
async def get_stock_price(symbol: str):
    """
    Get price data for a specific stock.

    Args:
        symbol: Stock symbol (e.g., "SCOM")

    Returns:
        Stock price data or 404 if not found
    """
    symbol = symbol.upper()

    try:
        price_data = await get_price(symbol)

        if not price_data:
            # Try demo data
            demo_prices = get_demo_prices()
            for p in demo_prices:
                if p["symbol"] == symbol:
                    p["name"] = get_company_name(symbol)
                    p["formatted_price"] = format_price(p["price"])
                    p["formatted_change"] = format_change(p["change"], p["change_percent"])
                    return p
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")

        price_data["name"] = get_company_name(symbol)
        price_data["formatted_price"] = format_price(price_data["price"])
        price_data["formatted_change"] = format_change(price_data["change"], price_data["change_percent"])

        return price_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching price for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching price: {str(e)}")


# Company name mapping (same as sentiment_fusion)
COMPANY_NAMES = {
    "SCOM": "Safaricom PLC",
    "EQTY": "Equity Group Holdings",
    "KCB": "KCB Group",
    "ABSA": "Absa Bank Kenya",
    "EABL": "East African Breweries",
    "BAMB": "Bamburi Cement",
    "COOP": "Cooperative Bank",
    "NMG": "Nation Media Group",
    "JUBH": "Jubilee Holdings",
    "CNTY": "Centum Investment",
    "KAPC": "Kenya Airways",
    "KENG": "KenGen",
    "TKN": "Telkom Kenya",
    "BAT": "British American Tobacco",
    "ARM": "ARM Cement",
    "BRCK": "Brimstone Investment",
    "LKL": "Liberty Holdings",
    "SPWN": "Spencer Flowers",
    "WTKR": "Walters Kenya",
    "KNRE": "Kenya Re",
    "BRIT": "British American Tobacco (Britak)",
    "MSC": "Mobius Investment Trust",
}


def get_company_name(symbol: str) -> str:
    """Get full company name from symbol."""
    return COMPANY_NAMES.get(symbol, symbol)


@router.get("/companies")
async def get_companies(
    ibuka_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of NSE and Ibuka companies.
    """
    query = select(Company)
    if ibuka_only:
        query = query.where(Company.is_ibuka == True)

    query = query.order_by(Company.symbol)

    result = await db.execute(query)
    companies = result.scalars().all()

    return {
        "companies": [
            {
                "symbol": c.symbol,
                "name": c.name,
                "sector": c.sector,
                "is_ibuka": c.is_ibuka
            }
            for c in companies
        ],
        "source": "NSE public data"
    }


@router.get("/index")
async def get_market_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Get market index summary (NASI, NSE 20, NSE 25).
    Demo endpoint - returns static data for prototype.
    """
    return {
        "indices": {
            "NASI": {"value": 192.45, "change": 0.82, "change_pct": 0.43},
            "NSE 20": {"value": 2847.32, "change": -12.45, "change_pct": -0.44},
            "NSE 25": {"value": 3124.18, "change": 8.67, "change_pct": 0.28}
        },
        "market_status": "open",
        "last_update": datetime.utcnow().isoformat(),
        "source": "NSE public data",
        "note": "Demo data for prototype purposes"
    }
