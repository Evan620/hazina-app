"""
Database configuration and connection management
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Float, Integer, DateTime, Text, Boolean, JSON
from datetime import datetime
import os

# Railway provides DATABASE_URL via service reference or RAILWAY_DATABASE_URL
# Try both, falling back to SQLite for local development
DATABASE_URL = (
    os.getenv("DATABASE_URL") or
    os.getenv("RAILWAY_DATABASE_URL") or
    "sqlite+aiosqlite:///hazina.db"
)

# Convert PostgreSQL URL to use asyncpg driver for async SQLAlchemy
# Railway provides postgresql:// which defaults to psycopg2 (sync)
# Also handle postgresqleu:// (some Railway configs)
if DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "", 1).replace("postgres://", "", 1)
    DATABASE_URL = f"postgresql+asyncpg://{DATABASE_URL}"

# For SQLite, we need to use an absolute path or properly formatted relative path
if DATABASE_URL.startswith("sqlite+aiosqlite://./"):
    # Convert relative path to absolute path
    import pathlib
    db_path = pathlib.Path(__file__).parent.parent.parent / DATABASE_URL.split("://./")[1]
    DATABASE_URL = f"sqlite+aiosqlite:///{db_path.absolute()}"

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to False in production
    future=True,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Database models
class Company(Base):
    """NSE and Ibuka companies."""
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str] = mapped_column(String(100), nullable=True)
    is_ibuka: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MarketData(Base):
    """Daily equity price data."""
    __tablename__ = "market_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
    change_pct: Mapped[float] = mapped_column(Float, nullable=True)
    volume: Mapped[int] = mapped_column(Integer, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class SentimentSignal(Base):
    """NLP-derived sentiment signals from news."""
    __tablename__ = "sentiment_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_mentioned: Mapped[str] = mapped_column(String(100), index=True)
    sentiment: Mapped[str] = mapped_column(String(20))  # positive/negative/neutral
    confidence: Mapped[float] = mapped_column(Float)  # 0-1
    key_reason: Mapped[str] = mapped_column(Text)
    relevant_to_investors: Mapped[bool] = mapped_column(Boolean, default=True)
    article_url: Mapped[str] = mapped_column(String(500), nullable=True)
    article_title: Mapped[str] = mapped_column(String(500), nullable=True)
    source: Mapped[str] = mapped_column(String(100))  # Business Daily, Reuters, etc.
    snippet: Mapped[str] = mapped_column(Text, nullable=True)  # Relevant text excerpt
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ListingScore(Base):
    """Listing readiness scores for companies."""
    __tablename__ = "listing_scores"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=True)

    # 6 dimension scores (0-10 each)
    revenue_score: Mapped[int] = mapped_column(Integer)
    governance_score: Mapped[int] = mapped_column(Integer)
    growth_score: Mapped[int] = mapped_column(Integer)
    compliance_score: Mapped[int] = mapped_column(Integer)
    market_size_score: Mapped[int] = mapped_column(Integer)
    timing_score: Mapped[int] = mapped_column(Integer)

    # Overall score
    overall_score: Mapped[int] = mapped_column(Integer)  # 0-100
    recommendation: Mapped[str] = mapped_column(String(50))  # Ready/Needs Work/Not Ready

    # Detailed breakdowns (JSON)
    revenue_breakdown: Mapped[dict] = mapped_column(JSON, nullable=True)
    governance_breakdown: Mapped[dict] = mapped_column(JSON, nullable=True)
    growth_breakdown: Mapped[dict] = mapped_column(JSON, nullable=True)
    compliance_breakdown: Mapped[dict] = mapped_column(JSON, nullable=True)
    market_size_breakdown: Mapped[dict] = mapped_column(JSON, nullable=True)
    timing_breakdown: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Metadata
    data_sources: Mapped[list] = mapped_column(JSON, nullable=True)  # List of sources used
    overall_confidence: Mapped[str] = mapped_column(String(20))  # High/Medium/Low

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class StockPrediction(Base):
    """Cached AI price predictions for NSE stocks. Updated 3x daily."""
    __tablename__ = "stock_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)

    # Current price
    current_price: Mapped[float] = mapped_column(Float, nullable=True)

    # Sentiment scores
    overall_sentiment: Mapped[float] = mapped_column(Float, default=0.5)  # 0-1
    news_sentiment: Mapped[float] = mapped_column(Float, default=0.5)  # 0-1
    twitter_sentiment: Mapped[float] = mapped_column(Float, default=0.5)  # 0-1

    # Signal count
    signal_count: Mapped[int] = mapped_column(Integer, default=0)

    # Predictions (JSON array)
    predictions: Mapped[dict] = mapped_column(JSON)  # {horizon_days, direction, confidence, reasoning}[]

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
