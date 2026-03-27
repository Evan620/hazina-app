# Hazina

AI-powered investor intelligence platform for the Nairobi Securities Exchange (NSE).

"Hazina" means "treasure" in Swahili.

## Overview

Hazina is a two-sided platform:

- **For Companies**: Listing Readiness Scanner — helps SMEs understand if they're ready to list on NSE Ibuka
- **For Investors/Brokers**: Market Sentiment Dashboard — AI-driven signals on NSE equities

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.12 + FastAPI |
| AI/LLM | Anthropic Claude API |
| Frontend | React 18 + Tailwind CSS + Recharts |
| Database | PostgreSQL 16 + TimescaleDB |
| Caching | Redis |
| Scraping | httpx + BeautifulSoup + Playwright |
| NLP | spaCy + Claude API |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (or Docker)
- Redis (or Docker)
- Anthropic API key

### Option 1: Docker Compose (Recommended)

```bash
# Copy environment file
cp .env.example .env

# Add your Anthropic API key to .env

# Start all services
docker-compose up -d

# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up database (create hazina db)
createdb hazina

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://hazina:hazina@localhost:5432/hazina"
export ANTHROPIC_API_KEY="your_key_here"

# Run backend
uvicorn app.main:app --reload
```

**Frontend:**
```bash
npm install
npm run dev
```

## API Endpoints

### Market Data
- `GET /api/v1/market/prices` — Latest NSE prices
- `GET /api/v1/market/companies` — List of NSE/Ibuka companies
- `GET /api/v1/market/index` — Market index summary

### Sentiment Analysis
- `GET /api/v1/sentiment/signals` — Latest sentiment signals
- `GET /api/v1/sentiment/feed` — Chronological sentiment feed
- `GET /api/v1/sentiment/summary/{symbol}` — Company sentiment summary

### Listing Readiness Scanner
- `POST /api/v1/listing/scan` — Analyze company listing readiness
- `GET /api/v1/listing/companies` — List scanned companies

### Prospectus Compliance Checker
- `POST /api/v1/prospectus/check` — Upload PDF for compliance check
- `GET /api/v1/prospectus/requirements` — CMA requirements reference

## Project Status

**Phase: PROTOTYPE** — Demo for NSE CEO Frank Mwiti

- ✅ Frontend demo with 5 tabs
- ✅ Backend API scaffolded
- ✅ Database schema defined
- ⏳ Real-time NSE data scraping (pending vendor agreement)
- ⏳ News sentiment pipeline
- ⏳ Claude API integration

## License

Proprietary — AfCEN

## Contact

AfCEN — AI-powered capital markets solutions for Africa
