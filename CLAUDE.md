# Hazina — Claude Code Instructions

## What This Is
AI-powered NSE investor intelligence platform. Two sides: (1) Listing Readiness Scanner for companies, (2) Market Sentiment Dashboard for investors.

## Rules
- Python 3.12 + FastAPI backend
- React 18 + Tailwind frontend
- PostgreSQL for persistence, Redis for caching
- Never fabricate financial data. If data is unavailable, return a clear error.
- All Claude API calls use claude-sonnet-4-20250514 model
- Keep API keys in .env, never hardcode

## Current Phase: PROTOTYPE
We are building a demo for NSE CEO Frank Mwiti. No NSE vendor agreement yet.
- Use public NSE data (scrape https://www.nse.co.ke/live-market/)
- Use public Kenyan news (Business Daily Africa, Reuters Africa, The Star)
- Mark all scraped data clearly as "public source" in the UI
- Real-time data comes later once vendor agreement is signed

## Module Priority
1. Listing Readiness Scanner (most impressive for demo)
2. Market Sentiment Dashboard (visual impact)
3. Prospectus Compliance Checker (no live data needed — easiest)

## API Keys (set in .env)
- ANTHROPIC_API_KEY — for all Claude API calls
- DATABASE_URL — postgres connection string
- REDIS_URL — redis connection string

## Repository Structure
```
hazina-app/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── api/v1/
│   │   │   ├── sentiment.py     # Sentiment engine endpoints
│   │   │   ├── listing.py       # Listing Readiness Scanner endpoints
│   │   │   ├── prospectus.py    # Prospectus checker endpoints
│   │   │   └── market.py        # Market data endpoints
│   │   ├── services/
│   │   │   ├── nse_scraper.py       # NSE public data scraper
│   │   │   ├── news_scraper.py      # Business Daily, Reuters, The Star
│   │   │   ├── sentiment_engine.py  # NLP + Claude API sentiment
│   │   │   ├── listing_scorer.py    # 6-dimension listing readiness
│   │   │   └── prospectus_ai.py     # Claude API prospectus analysis
│   │   ├── models/
│   │   └── db/
│   │       └── database.py      # SQLAlchemy models + connection
├── frontend/ (root level)
│   ├── src/
│   │   ├── App.tsx
│   │   ├── HazinaDemo.tsx       # The demo Joseph built
│   │   └── ...
│   ├── docker-compose.yml
│   └── .env.example
```

## Key Constraint: Chinese Wall
Information barrier between listing intelligence and market data products is REGULATORY NON-OPTIONAL.
- Companies using Listing Scanner must NOT have access to non-public market data
- Must implement before beta launch
- Lazarus owns this requirement

## Demo Script (for Frank Mwiti)
1. Dashboard (2 min) — Show sentiment feed for SCOM, EQTY, KCB
2. Listing Scanner (8 min) — Run on Copy Cat, Koko Networks
3. Prospectus Check (5 min) — Upload sample draft prospectus
4. API tiers (5 min) — Show revenue model

Key message: "We built this without your data. Imagine what it looks like once we have the real NSE feed."
