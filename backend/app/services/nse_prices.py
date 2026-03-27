"""
NSE Live Market Prices Service
Fetches real-time stock prices from NSE via deveintapps API
"""

import httpx
from datetime import datetime
from typing import List, Dict, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

# NSE external API endpoint
NSE_PRICE_API = "https://deveintapps.com/nseticker/api/v1/ticker"
NSE_ISIN = "KE3000009674"  # Default ISIN for NSE market data

# Cache for prices (to avoid rate limiting)
_price_cache: Dict[str, Dict] = {}
_cache_timestamp: Optional[datetime] = None
CACHE_DURATION_SECONDS = 60  # Cache for 1 minute


async def fetch_nse_prices() -> List[Dict]:
    """
    Fetch live NSE stock prices from external API.

    Returns:
        List of stock price data:
        [{
            "issuer": "SCOM",
            "price": 27.95,
            "prev_price": 27.95,
            "change": 0,
            "today_open": 28,
            "today_high": 29,
            "today_low": 27.9,
            "volume": 3453330,
            "turnover": 96861651.5
        }, ...]
    """
    global _price_cache, _cache_timestamp

    # Check cache
    if _cache_timestamp:
        age = (datetime.utcnow() - _cache_timestamp).total_seconds()
        if age < CACHE_DURATION_SECONDS:
            logger.debug(f"Using cached prices (age: {age:.1f}s)")
            return list(_price_cache.values())

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                NSE_PRICE_API,
                json={"nopage": "true", "isinno": NSE_ISIN},
                headers={
                    "Referer": "https://www.nse.co.ke/",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            response.raise_for_status()

            data = response.json()

            if "message" in data and isinstance(data["message"], list) and len(data["message"]) > 0:
                snapshot_data = data["message"][0].get("snapshot", [])

                # Convert to dict keyed by issuer for O(1) lookup
                prices_by_symbol = {}
                for item in snapshot_data:
                    symbol = item.get("issuer")
                    if symbol:
                        # Extract key fields
                        prices_by_symbol[symbol] = {
                            "symbol": symbol,
                            "price": float(item.get("price", 0) or 0),
                            "prev_price": float(item.get("prev_price", 0) or 0),
                            "change": float(item.get("change", 0) or 0),
                            "change_percent": calculate_change_percent(item),
                            "today_open": float(item.get("today_open", 0) or 0),
                            "today_high": float(item.get("today_high", 0) or 0),
                            "today_low": float(item.get("today_low", 0) or 0),
                            "volume": int(item.get("volume", 0) or 0),
                            "turnover": float(item.get("turnover", 0) or 0),
                            "last_updated": datetime.utcnow().isoformat()
                        }

                # Update cache
                _price_cache = prices_by_symbol
                _cache_timestamp = datetime.utcnow()

                logger.info(f"Fetched {len(prices_by_symbol)} stock prices from NSE")
                return list(prices_by_symbol.values())

            else:
                logger.warning(f"Unexpected API response format: {data}")
                return []

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching NSE prices: {e}")
        return []
    except Exception as e:
        logger.error(f"Error fetching NSE prices: {e}")
        return []


def calculate_change_percent(item: Dict) -> float:
    """Calculate percentage change from previous price."""
    current = float(item.get("price", 0) or 0)
    prev = float(item.get("prev_price", 0) or 0)

    if prev == 0:
        return 0.0

    return ((current - prev) / prev) * 100


def get_cached_price(symbol: str) -> Optional[Dict]:
    """Get cached price for a specific symbol."""
    return _price_cache.get(symbol.upper())


async def get_price(symbol: str) -> Optional[Dict]:
    """
    Get current price for a specific symbol.

    Args:
        symbol: Stock symbol (e.g., "SCOM")

    Returns:
        Price data dict or None if not found
    """
    if _cache_timestamp is None:
        await fetch_nse_prices()

    return get_cached_price(symbol)


def format_price(price: float) -> str:
    """Format price as KES string."""
    return f"KES {price:,.2f}"


def format_change(change: float, change_percent: float) -> str:
    """Format change with sign indicator."""
    sign = "+" if change > 0 else ""
    return f"{sign}{change_percent:.2f}%"


# Demo fallback data
def get_demo_prices() -> List[Dict]:
    """Return demo price data for testing when API is unavailable."""
    return [
        {
            "symbol": "SCOM",
            "price": 38.50,
            "prev_price": 38.00,
            "change": 0.50,
            "change_percent": 1.32,
            "today_open": 38.25,
            "today_high": 39.00,
            "today_low": 38.00,
            "volume": 15000000,
            "turnover": 577500000,
            "last_updated": datetime.utcnow().isoformat()
        },
        {
            "symbol": "EQTY",
            "price": 69.75,
            "prev_price": 67.25,
            "change": 2.50,
            "change_percent": 3.72,
            "today_open": 69.00,
            "today_high": 72.00,
            "today_low": 67.75,
            "volume": 3402409,
            "turnover": 234340017,
            "last_updated": datetime.utcnow().isoformat()
        },
        {
            "symbol": "KCB",
            "price": 68.50,
            "prev_price": 66.50,
            "change": 2.00,
            "change_percent": 3.01,
            "today_open": 67.00,
            "today_high": 70.00,
            "today_low": 66.25,
            "volume": 1016619,
            "turnover": 69155453,
            "last_updated": datetime.utcnow().isoformat()
        },
        {
            "symbol": "ABSA",
            "price": 18.25,
            "prev_price": 18.10,
            "change": 0.15,
            "change_percent": 0.83,
            "today_open": 18.15,
            "today_high": 18.40,
            "today_low": 18.10,
            "volume": 850000,
            "turnover": 15512500,
            "last_updated": datetime.utcnow().isoformat()
        },
        {
            "symbol": "EABL",
            "price": 142.00,
            "prev_price": 143.50,
            "change": -1.50,
            "change_percent": -1.05,
            "today_open": 143.00,
            "today_high": 143.25,
            "today_low": 141.50,
            "volume": 425000,
            "turnover": 60685000,
            "last_updated": datetime.utcnow().isoformat()
        },
    ]


if __name__ == "__main__":
    # Test the price fetcher
    import asyncio

    async def test():
        prices = await fetch_nse_prices()
        print(f"Fetched {len(prices)} prices:")
        for p in prices[:5]:
            print(f"  {p['symbol']}: {format_price(p['price'])} ({format_change(p['change'], p['change_percent'])})")

    asyncio.run(test())
