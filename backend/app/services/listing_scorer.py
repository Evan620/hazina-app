"""
Listing Readiness Scanner Service
Uses Claude API to analyze companies across 6 dimensions
"""

import os
import anthropic
from datetime import datetime
from typing import Dict, List, Optional
import httpx
from bs4 import BeautifulSoup

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# System prompt for listing readiness analysis
LISTING_ANALYSIS_PROMPT = """You are a capital markets expert specializing in Nairobi Securities Exchange (NSE) listings, particularly the Ibuka SME segment.

Analyze the company based on the provided information and score it across 6 dimensions (0-10 scale for each):

1. **Revenue** - Turnover stability, growth trajectory, financial consistency
2. **Governance** - Board composition, audit quality, ownership structure
3. **Growth** - Market opportunity, competitive position, scalability
4. **Compliance** - Regulatory filings, tax compliance, legal standing
5. **Market Size** - Total addressable market in Kenya, sector potential
6. **Timing** - Current NSE market conditions, sector cycle position

For each dimension, provide:
- score (0-10)
- confidence (High/Medium/Low)
- reasoning (2-3 sentences explaining the score)
- data_source (what information the score is based on)

Also provide:
- overall_score (0-100, weighted average of dimensions)
- recommendation (Ready/Needs Work/Not Ready)
- overall_confidence (High/Medium/Low)

IMPORTANT CONSTRAINTS:
- Be conservative with scores - listing is a high bar
- If information is insufficient, give lower scores with Low confidence
- NEVER fabricate financial data
- Always cite the data source used
- Consider Kenya-specific market context

Return ONLY valid JSON in this exact format:
{
  "scores": {
    "revenue": 0-10,
    "governance": 0-10,
    "growth": 0-10,
    "compliance": 0-10,
    "market_size": 0-10,
    "timing": 0-10
  },
  "breakdowns": {
    "revenue": {"score": 0-10, "confidence": "High/Medium/Low", "reasoning": "...", "data_source": "..."},
    "governance": {"score": 0-10, "confidence": "High/Medium/Low", "reasoning": "...", "data_source": "..."},
    "growth": {"score": 0-10, "confidence": "High/Medium/Low", "reasoning": "...", "data_source": "..."},
    "compliance": {"score": 0-10, "confidence": "High/Medium/Low", "reasoning": "...", "data_source": "..."},
    "market_size": {"score": 0-10, "confidence": "High/Medium/Low", "reasoning": "...", "data_source": "..."},
    "timing": {"score": 0-10, "confidence": "High/Medium/Low", "reasoning": "...", "data_source": "..."}
  },
  "overall_score": 0-100,
  "recommendation": "Ready/Needs Work/Not Ready",
  "confidence": "High/Medium/Low",
  "data_sources": ["list of sources used"]
}
"""


async def search_company_info(company_name: str) -> Dict:
    """
    Search for publicly available information about the company.
    Returns basic info from web search and news.
    """
    info = {
        "basic_info": {},
        "news_articles": [],
        "sources": []
    }

    # Try to get info from Kenyan business directories and news
    # This is a placeholder - in production, use actual web scraping
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Search Business Daily Africa
            search_url = f"https://www.businessdailyafrica.com/search?q={company_name}"
            info["sources"].append("Business Daily Africa (public search)")
    except Exception as e:
        pass

    return info


async def analyze_company_readiness(
    company_name: str,
    symbol: Optional[str] = None
) -> Dict:
    """
    Analyze a company's listing readiness using Claude API.

    Args:
        company_name: Name of the company to analyze
        symbol: Optional stock symbol (if publicly traded elsewhere)

    Returns:
        Dict with scores, breakdowns, and recommendation
    """
    # Gather available information
    company_info = await search_company_info(company_name)

    # Build prompt for Claude
    prompt = f"""Analyze the following company for NSE Ibuka listing readiness:

Company: {company_name}
{f'Symbol: {symbol}' if symbol else ''}

Available Public Information:
{company_info}

Please provide the 6-dimension analysis as specified in the system prompt."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            temperature=0.3,  # Lower temperature for more consistent scoring
            system=LISTING_ANALYSIS_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse response
        import json
        response_text = response.content[0].text

        # Try to extract JSON from response
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)

        # Add metadata
        result["analyzed_at"] = datetime.utcnow().isoformat()
        result["data_sources"] = result.get("data_sources", []) + ["Public web search", "Claude API analysis"]

        return result

    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse analysis response",
            "raw_response": response_text if 'response_text' in locals() else "No response"
        }
    except Exception as e:
        return {
            "error": f"Analysis failed: {str(e)}",
            "company": company_name
        }


# Demo data for testing without API key
DEMO_COMPANIES = {
    "Copy Cat Limited": {
        "scores": {"revenue": 7, "governance": 6, "growth": 8, "compliance": 5, "market_size": 7, "timing": 6},
        "breakdowns": {
            "revenue": {"score": 7, "confidence": "Medium", "reasoning": "Strong growth in baked goods category, though margins are pressure from input costs.", "data_source": "News articles, industry reports"},
            "governance": {"score": 6, "confidence": "Medium", "reasoning": "Family-owned with transition to professional management. Board structure needs strengthening.", "data_source": "Company announcements"},
            "growth": {"score": 8, "confidence": "High", "reasoning": "Kenyan bakery market growing at 8% CAGR. Copy Cat is a leader in baked snacks.", "data_source": "Sector analysis"},
            "compliance": {"score": 5, "confidence": "Medium", "reasoning": "Some tax compliance questions from recent audits. Needs clean record before listing.", "data_source": "Public records"},
            "market_size": {"score": 7, "confidence": "High", "reasoning": "Informal sector formalization driving packaged foods demand. TAM ~KES 150B.", "data_source": "Market research"},
            "timing": {"score": 6, "confidence": "Medium", "reasoning": "NSE conditions moderate. Consumer sector facing headwinds but defensive.", "data_source": "NSE market data"}
        },
        "overall_score": 66,
        "recommendation": "Needs Work",
        "confidence": "Medium",
        "data_sources": ["News articles", "Company announcements", "Sector analysis"]
    },
    "Koko Networks": {
        "scores": {"revenue": 6, "governance": 7, "growth": 9, "compliance": 6, "market_size": 8, "timing": 7},
        "breakdowns": {
            "revenue": {"score": 6, "confidence": "Medium", "reasoning": "Strong user growth (2M+ customers) but monetization still early stage.", "data_source": "Company reports, news"},
            "governance": {"score": 7, "confidence": "Medium", "reasoning": "Strong founder background, international VC backing. Board needs independent directors.", "data_source": "Company announcements"},
            "growth": {"score": 9, "confidence": "High", "reasoning": "Energy access market huge. LPG distribution model scalable across East Africa.", "data_source": "Sector analysis"},
            "compliance": {"score": 6, "confidence": "Medium", "reasoning": "Generally clean, but energy sector has additional regulatory requirements.", "data_source": "EPRA regulations"},
            "market_size": {"score": 8, "confidence": "High", "reasoning": "Kenya LPG market ~$500M with double-digit growth. Regional expansion potential.", "data_source": "Energy sector reports"},
            "timing": {"score": 7, "confidence": "Medium", "reasoning": "Energy transition theme favorable. ESG angle attractive for investors.", "data_source": "Market conditions"}
        },
        "overall_score": 72,
        "recommendation": "Needs Work",
        "confidence": "Medium",
        "data_sources": ["Company reports", "Energy sector analysis", "News coverage"]
    },
    "Mastermind Tobacco": {
        "scores": {"revenue": 8, "governance": 7, "growth": 5, "compliance": 6, "market_size": 5, "timing": 4},
        "breakdowns": {
            "revenue": {"score": 8, "confidence": "High", "reasoning": "Consistent revenue stream, strong cash generation, established distribution.", "data_source": "Industry reports"},
            "governance": {"score": 7, "confidence": "Medium", "reasoning": "Professional management in place. Ownership concentration needs disclosure.", "data_source": "Company records"},
            "growth": {"score": 5, "confidence": "Medium", "reasoning": "Tobacco sector stagnant. Regulatory pressure increasing globally and locally.", "data_source": "Sector trends"},
            "compliance": {"score": 6, "confidence": "Medium", "reasoning": "Historical compliance issues with excise tax. Now largely resolved.", "data_source": "KRA records"},
            "market_size": {"score": 5, "confidence": "Medium", "reasoning": "Declining smoking prevalence. Limited growth in traditional tobacco.", "data_source": "WHO reports, local surveys"},
            "timing": {"score": 4, "confidence": "Medium", "reasoning": "ESG concerns around tobacco. Not ideal timing for consumer-facing listing.", "data_source": "Market sentiment"}
        },
        "overall_score": 58,
        "recommendation": "Not Ready",
        "confidence": "Medium",
        "data_sources": ["Industry reports", "KRA records", "Sector trends"]
    }
}


async def get_demo_analysis(company_name: str) -> Optional[Dict]:
    """Get demo analysis if company matches demo data."""
    for key, data in DEMO_COMPANIES.items():
        if company_name.lower() in key.lower() or key.lower() in company_name.lower():
            result = data.copy()
            result["analyzed_at"] = datetime.utcnow().isoformat()
            return result
    return None


# ============================================================================
# HYBRID ANALYSIS - Company Input + Public Verification
# ============================================================================

async def analyze_company_readiness_hybrid(
    company_input: Dict,
    verification_result: Dict,
    document_verification: Optional[Dict] = None,
    manual_verification: Optional[Dict] = None
) -> Dict:
    """
    Analyze listing readiness using company-provided data + verification.

    Args:
        company_input: {
            "name": str,
            "sector": str,
            "website": str,
            "segment": str,  # GEMS/AIMS/MIMS
            "issued_share_capital": int,
            "shareholders_count": int,
            "free_float_percent": int,
            "trading_years": float,
            "revenue_history": {year: float, ...},
            "board_members": [{"name": str, "role": str, "independent": bool}, ...],
            "tax_compliant": bool,
            "licenses": List[str],
            "litigation": str,
            "key_parties": List[str],
            "documents_ready": List[str],
            # NEW for manual verification
            "auditor_contact": Optional[str],
            "kra_pin": Optional[str],
            "crd_reference": Optional[str],
        }
        verification_result: Output from verifier.py
        document_verification: Optional dict with document verification results
        manual_verification: Optional dict with manual code verification results

    Returns:
        {
            "company_health": {scores, overall_score, recommendation, ...},
            "regulatory_readiness": {regulatory_score, requirements, parties, documents, ...},
            "combined_recommendation": "...",
            "verification": verification_result,
            "document_verification": document_verification,
            "manual_verification": manual_verification,
            "data_sources": [...]
        }
    """
    segment = company_input.get("segment", "GEMS")

    # Calculate base scores from company input (Company Health)
    scores = {
        "revenue": score_revenue_from_input(company_input),
        "governance": score_governance_from_input(company_input),
        "growth": score_growth_from_input(company_input),
        "compliance": score_compliance_from_input(company_input),
        "market_size": estimate_market_size(company_input.get("sector", "")),
        "timing": await get_timing_score()  # Use sentiment engine for timing
    }

    # Adjust scores based on verification results
    # Only penalize for REAL discrepancies (actual public data, not NSE rules comparisons)
    for discrepancy in verification_result.get("discrepancies", []):
        source = discrepancy.get("source", "")
        # Skip penalties for rule-based "discrepancies" that aren't actual public data
        if "NSE" in source or "rule" in source.lower():
            continue
        dimension = map_field_to_dimension(discrepancy.get("field", ""))
        if dimension and dimension in scores:
            # Apply 30% penalty for real public data discrepancies (reduced from 50%)
            scores[dimension] = max(0, int(scores[dimension] * 0.7))

    # Additional penalty for compliance red flags
    for flag in verification_result.get("red_flags", []):
        if flag.get("field") == "compliance":
            severity = flag.get("severity", "medium")
            penalty = 20 if severity == "high" else 10 if severity == "medium" else 5
            scores["compliance"] = max(0, scores["compliance"] - penalty)

    # Add trust bonus if verification is strong
    if verification_result.get("trust_score", 0) > 0.8:
        for key in scores:
            scores[key] = min(10, scores[key] + 1)

    # Calculate overall company health score (0-100)
    overall = sum(scores.values()) / len(scores) * 10

    # Determine company health recommendation
    if overall >= 70:
        recommendation = "Ready"
    elif overall >= 50:
        recommendation = "Needs Work"
    else:
        recommendation = "Not Ready"

    # Generate breakdowns with honest verification sourcing
    breakdowns = await generate_breakdowns(
        scores,
        company_input,
        verification_result,
        document_verification=document_verification,
        manual_verification=manual_verification
    )

    # NEW: Check Regulatory Readiness (NSE segment-specific)
    regulatory = check_regulatory_readiness(
        segment=segment,
        company_data=company_input,
        parties_appointed=company_input.get("key_parties", []),
        documents_ready=company_input.get("documents_ready", [])
    )

    # NEW: Generate combined recommendation
    combined_rec = generate_combined_recommendation(
        regulatory_score=regulatory["regulatory_score"],
        company_health_score=int(overall),
        segment=segment
    )

    return {
        # Company Health (6 dimensions)
        "company_health": {
            "scores": scores,
            "breakdowns": breakdowns,
            "overall_score": int(overall),
            "recommendation": recommendation,
            "segment": segment,
        },
        # Regulatory Readiness (NSE-specific)
        "regulatory_readiness": regulatory,
        # Combined Analysis
        "combined_recommendation": combined_rec,
        # Verification data
        "verification": verification_result,
        "document_verification": document_verification or {},
        "manual_verification": manual_verification or {},
        "data_sources": ["Company input"] + verification_result.get("sources_used", [])
    }


def score_revenue_from_input(input_data: Dict) -> int:
    """Score revenue dimension (0-10) based on company input."""
    revenue_history = input_data.get("revenue_history", {})
    if not revenue_history:
        return 3

    # Convert string keys to integers for comparison
    try:
        years = [int(y) for y in revenue_history.keys()]
    except (ValueError, TypeError):
        return 3

    if len(years) < 2:
        return 3

    first_year = min(years)
    last_year = max(years)
    start = revenue_history[str(first_year)]
    end = revenue_history[str(last_year)]

    if start <= 0:
        return 2

    # Calculate CAGR
    years_span = last_year - first_year
    if years_span == 0:
        years_span = 1

    cagr = ((end / start) ** (1 / years_span)) - 1

    # Score based on growth rate
    if cagr >= 0.20:  # 20%+ growth
        return 10
    elif cagr >= 0.15:
        return 9
    elif cagr >= 0.10:
        return 8
    elif cagr >= 0.05:
        return 6
    elif cagr >= 0:
        return 4
    else:
        return 2


def score_governance_from_input(input_data: Dict) -> int:
    """Score governance dimension (0-10) based on board composition."""
    board = input_data.get("board_members", [])
    if not board:
        return 3

    # Normalize board members - handle both string format and dict format
    normalized_board = []
    for b in board:
        if isinstance(b, str):
            # String format like "John Doe" or "John Doe - CEO"
            name = b.split(" - ")[0].strip()
            is_independent = any(word in b.lower() for word in ["independent", "non-exec", "non exec"])
            normalized_board.append({"name": name, "independent": is_independent})
        elif isinstance(b, dict):
            # Already in dict format
            normalized_board.append(b)

    # Count valid board members (with names)
    valid_board = [b for b in normalized_board if b.get("name") and len(b.get("name", "")) > 2]
    total_count = len(valid_board)

    if total_count < 3:
        return 2  # Below minimum requirement

    independent_count = sum(1 for b in valid_board if b.get("independent"))
    independent_ratio = independent_count / total_count if total_count > 0 else 0

    # NSE requires at least 50% independent directors
    if total_count >= 5 and independent_ratio >= 0.5:
        return 10
    elif total_count >= 5 and independent_ratio >= 0.3:
        return 8
    elif total_count >= 3 and independent_count >= 1:
        return 6
    elif total_count >= 3:
        return 4
    else:
        return 3


def score_growth_from_input(input_data: Dict) -> int:
    """Score growth dimension (0-10) using revenue as proxy plus sector factor."""
    revenue_score = score_revenue_from_input(input_data)

    # Sector growth multiplier
    sector = input_data.get("sector", "").lower()
    high_growth_sectors = ["technology", "energy", "fintech", "agriculture", "renewable"]
    medium_growth_sectors = ["retail", "fmcg", "telecom", "health"]

    if any(s in sector for s in high_growth_sectors):
        return min(10, revenue_score + 2)
    elif any(s in sector for s in medium_growth_sectors):
        return min(10, revenue_score + 1)
    else:
        return revenue_score


def score_compliance_from_input(input_data: Dict) -> int:
    """Score compliance dimension (0-10) based on company declarations."""
    score = 7  # Base score

    # Tax compliance is critical
    if not input_data.get("tax_compliant"):
        score -= 4

    # Active litigation reduces score
    if input_data.get("litigation"):
        score -= 2

    # Licenses indicate regulatory compliance
    licenses = input_data.get("licenses", [])
    if not licenses or len(licenses) == 0:
        score -= 1
    else:
        score += 1

    return max(0, min(10, score))


def estimate_market_size(sector: str) -> int:
    """Estimate market size/opportunity score (0-10) by sector."""
    sector_sizes = {
        "retail": 8,
        "technology": 9,
        "fmcg": 8,
        "banking": 7,
        "finance": 7,
        "agriculture": 8,
        "agritech": 9,
        "manufacturing": 7,
        "energy": 8,
        "renewable": 9,
        "telecom": 7,
        "health": 8,
        "fintech": 9,
        "real": 6,
        "construction": 6,
        "transport": 7,
        "logistics": 7,
    }

    sector_lower = sector.lower()
    for key, value in sector_sizes.items():
        if key in sector_lower:
            return value

    return 5  # Default for unknown sectors


async def get_timing_score() -> int:
    """
    Get timing score (0-10) based on current market conditions.

    Uses aggregate market sentiment from all companies.
    """
    try:
        from app.services.prediction_engine import aggregate_sentiment

        # Get sentiment for a market proxy (equity index or large cap)
        # Use SCOM (Safaricom) as NSE market sentiment proxy
        sentiment_data = await aggregate_sentiment("SCOM", hours=24)

        overall = sentiment_data.get("overall", 0.5)
        signal_count = sentiment_data.get("signal_count", 0)

        # Convert 0-1 sentiment to 0-10 score
        # Below 0.3 = bearish (low score), 0.4-0.6 = neutral (mid), 0.7+ = bullish (high)
        if overall >= 0.65:
            return 9  # Bullish market - good timing
        elif overall >= 0.55:
            return 7  # Moderately bullish
        elif overall >= 0.45:
            return 5  # Neutral
        elif overall >= 0.35:
            return 3  # Bearish - poor timing
        else:
            return 2  # Very bearish - bad timing
    except Exception:
        return 5  # Default neutral on error


def map_field_to_dimension(field: str) -> Optional[str]:
    """Map verification field to scoring dimension."""
    mapping = {
        "revenue": "revenue",
        "board": "governance",
        "governance": "governance",
        "compliance": "compliance",
        "tax": "compliance",
        "employees": "growth",
        "website": "revenue",
    }
    return mapping.get(field.lower(), None)


async def generate_breakdowns(
    scores: Dict,
    company_input: Dict,
    verification: Dict,
    document_verification: Optional[Dict] = None,
    manual_verification: Optional[Dict] = None
) -> Dict:
    """Generate detailed breakdowns for each dimension with honest verification sourcing."""
    breakdowns = {}

    trust_level = verification.get("trust_score", 0.5)
    confidence = "High" if trust_level > 0.7 else "Medium" if trust_level > 0.4 else "Low"

    for dim, score in scores.items():
        # Use AI to generate dynamic, contextual reasoning for each dimension
        reasoning = await generate_ai_dimension_reasoning(
            dimension=dim,
            score=score,
            company_input=company_input,
            verification=verification,
            document_verification=document_verification
        )

        # Check if THIS dimension has specific verification
        # Public verification for this specific dimension
        has_public_for_dim = (
            verification.get("confirmations") and
            any(map_field_to_dimension(c.get("field", "")) == dim
                for c in verification["confirmations"])
        )

        # Document verification mapping
        doc_map = {
            "revenue": "financials",
            "compliance": "tax_cert",
            "governance": "board_resolution"
        }
        doc_key = doc_map.get(dim)

        # Check if this dimension has document verification
        has_doc_for_dim = (
            document_verification and
            doc_key and
            doc_key in document_verification and
            document_verification[doc_key].get("verification_score", 0) > 0
        )

        # Determine honest data source PER DIMENSION
        if has_doc_for_dim:
            doc_result = document_verification[doc_key]
            issuer = doc_result.get("issuing_authority", "Uploaded document")
            conf = doc_result.get("confidence", "Medium")
            data_source = f"Document-based verification via {issuer}"
        elif has_public_for_dim:
            data_source = "Company input + public cross-check"
        elif manual_verification and manual_verification.get("overall_score", 0) > 0:
            data_source = "Manual code verification"
        else:
            data_source = "Company input only (no external verification)"

        breakdowns[dim] = {
            "score": score,
            "confidence": confidence,
            "reasoning": reasoning,
            "data_source": data_source
        }

    return breakdowns


async def generate_ai_dimension_reasoning(
    dimension: str,
    score: int,
    company_input: Dict,
    verification: Dict,
    document_verification: Optional[Dict] = None
) -> str:
    """
    Use Claude API to generate dynamic, contextual reasoning for each dimension.
    This replaces hardcoded templates with AI-generated insights.
    """
    dimension_names = {
        "revenue": "Revenue & Financial Performance",
        "governance": "Corporate Governance",
        "growth": "Growth Potential",
        "compliance": "Regulatory Compliance",
        "market_size": "Market Opportunity",
        "timing": "Market Timing"
    }

    # Build context based on dimension - using explicit get() calls
    context_parts = []

    # Define variables at function scope to avoid any scoping issues
    rh = company_input.get("revenue_history", {})
    bm = company_input.get("board_members", [])

    if dimension == "revenue":
        if rh:
            context_parts.append(f"Revenue History: {rh}")
        context_parts.append(f"Issued Share Capital: {company_input.get('issued_share_capital', 'N/A')}")
        if document_verification and document_verification.get("financials"):
            fin_doc = document_verification["financials"]
            context_parts.append(f"Financial Document Verified: {fin_doc.get('issuing_authority', 'Unknown')}")

    elif dimension == "governance":
        context_parts.append(f"Board Size: {len(bm)}")
        independent_count = sum(1 for m in bm if m.get("independent"))
        context_parts.append(f"Independent Directors: {independent_count}")
        if document_verification and document_verification.get("board_resolution"):
            br_doc = document_verification["board_resolution"]
            context_parts.append(f"Board Resolution Verified: {br_doc.get('issuing_authority', 'Unknown')}")

    elif dimension == "compliance":
        context_parts.append(f"Tax Compliant: {company_input.get('tax_compliant', 'N/A')}")
        context_parts.append(f"Litigation: {company_input.get('litigation', 'None')}")
        if document_verification and document_verification.get("tax_cert"):
            tc_doc = document_verification["tax_cert"]
            context_parts.append(f"Tax Certificate Verified: {tc_doc.get('issuing_authority', 'Unknown')}")

    elif dimension == "growth":
        context_parts.append(f"Sector: {company_input.get('sector', 'Unknown')}")
        if rh:
            context_parts.append(f"Revenue Data: {len(rh)} years provided")

    elif dimension == "market_size":
        context_parts.append(f"Sector: {company_input.get('sector', 'Unknown')}")
        context_parts.append(f"Segment Target: {company_input.get('segment', 'GEMS')}")

    elif dimension == "timing":
        context_parts.append("NSE current market conditions")

    # Add verification context if exists
    if verification.get("confirmations"):
        context_parts.append("Public data cross-check performed")

    if verification.get("discrepancies"):
        context_parts.append("Some discrepancies found with public data")

    prompt = f"""Analyze this company's {dimension_names.get(dimension, dimension)} and provide 2-3 sentences of reasoning.

Score: {score}/10

Company Context:
{chr(10).join(context_parts) if context_parts else "Limited data provided"}

Task: Provide concise, contextual reasoning for this score. Mention specific data points above. If score is low, explain what needs improvement. If score is high, highlight strengths.

Return ONLY the reasoning text, 2-3 sentences max."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )
        reasoning = response.content[0].text.strip()
        # Add qualitative assessment
        if score >= 8:
            reasoning += " Strong position for listing."
        elif score >= 6:
            reasoning += " Adequate, with room for improvement."
        elif score >= 4:
            reasoning += " Needs attention before listing."
        else:
            reasoning += " Significant gaps to address."
        return reasoning
    except Exception:
        return f"{dimension_names.get(dimension, dimension)} scored {score}/10. {('Strong' if score >= 7 else 'Needs improvement' if score >= 4 else 'Critical gaps')}."


# ============================================================================
# NSE SEGMENT-SPECIFIC REQUIREMENTS
# Source: NSE Guide to Listing (https://www.nse.co.ke/wp-content/uploads/guide-to-listing-2.pdf)
# ============================================================================

NSE_SEGMENT_REQUIREMENTS = {
    "GEMS": {
        "name": "Growth Enterprise Market Segment (GEMS)",
        "target": "SMEs and Startups",
        "source": "NSE Guide to Listing, Part C",
        "requirements": {
            "issued_share_capital": {"min": 10_000_000, "unit": "KES", "name": "Issued Share Capital"},
            "shares_in_issue": {"min": 100_000, "unit": "count", "name": "Minimum Shares in Issue"},
            "shareholders": {"min": 50, "unit": "count", "name": "Public Shareholders (15% float)"},
            "free_float": {"min": 15, "unit": "%", "name": "Free Float (public)"},
            "trading_years": {"min": 2, "unit": "years", "name": "Trading History", "waiver_possible": True},
            "profitability": {"min": 1, "unit": "years profits", "name": "Profitability (1 of 2 years)"}
        },
        "description": "Designed for growing SMEs with lower entry barriers",
        "official_note": "Must have 100,000 shares minimum, 15% to public, 2 years trading (1 year profit)"
    },
    "AIMS": {
        "name": "Alternative Investment Market Segment (AIMS)",
        "target": "Growing Companies",
        "source": "NSE Guide to Listing, Part B",
        "requirements": {
            "issued_share_capital": {"min": 20_000_000, "unit": "KES", "name": "Issued Share Capital"},
            "net_assets": {"min": 20_000_000, "unit": "KES", "name": "Net Assets"},
            "shareholders": {"min": 100, "unit": "count", "name": "Minimum Shareholders"},
            "free_float": {"min": 20, "unit": "%", "name": "Free Float (20% to public)"},
            "trading_years": {"min": 2, "unit": "years", "name": "Trading History with Profit", "waiver_possible": False},
            "profitability": {"min": 1, "unit": "years profits", "name": "Profitability (1 year profit)"}
        },
        "description": "For companies beyond startup stage, scaling toward main market",
        "official_note": "20% to at least 100 shareholders, net assets ≥ KES 20M, 2 years existence (1 profit)"
    },
    "MIMS": {
        "name": "Main Investment Market Segment (MIMS)",
        "target": "Established Blue-Chip Companies",
        "source": "NSE Guide to Listing, Part A",
        "requirements": {
            "issued_share_capital": {"min": 50_000_000, "unit": "KES", "name": "Issued Share Capital"},
            "net_assets": {"min": 100_000_000, "unit": "KES", "name": "Net Assets"},
            "shareholders": {"min": 1000, "unit": "count", "name": "Minimum Shareholders"},
            "free_float": {"min": 25, "unit": "%", "name": "Free Float (25% to public)"},
            "trading_years": {"min": 5, "unit": "years", "name": "Profitable Track Record", "waiver_possible": False},
            "profitability": {"min": 3, "unit": "years profits", "name": "Profitability (3 of 5 years)"}
        },
        "description": "Premier segment for established, profitable companies",
        "official_note": "25% to at least 1,000 shareholders, profits in 3 of last 5 years, net assets ≥ KES 100M"
    }
}

KEY_PARTIES = {
    "lead_transaction_advisor": {"name": "Lead Transaction Advisor", "essential": True, "description": "Coordinates the entire IPO process"},
    "sponsoring_broker": {"name": "Sponsoring Broker", "essential": True, "description": "NSE-licensed broker who sponsors the listing"},
    "legal_counsel": {"name": "Legal Counsel", "essential": True, "description": "Handles legal aspects and documentation"},
    "reporting_accountant": {"name": "Reporting Accountant", "essential": True, "description": "Prepares financial information and prospectus"},
    "receiving_agent": {"name": "Receiving Agent", "essential": False, "description": "Handles share applications and payments"},
    "trustee": {"name": "Trustee", "essential": False, "description": "Required for debt and REIT listings"}
}

REQUIRED_DOCUMENTS = {
    "certificate_of_incorporation": {"name": "Certificate of Incorporation", "essential": True},
    "audited_financials_2yr": {"name": "2 Years Audited Financials", "essential": True},
    "audited_financials_3yr": {"name": "3 Years Audited Financials", "essential": False},  # Only for MIMS
    "draft_prospectus": {"name": "Draft Prospectus", "essential": True},
    "cma_pre_approval": {"name": "CMA Pre-approval", "essential": False},  # Can apply without
    "board_approval": {"name": "Board Resolution to List", "essential": True},
    "shareholder_approval": {"name": "Shareholder Approval", "essential": False},
    "tax_compliance_certificate": {"name": "Tax Compliance Certificate", "essential": True},
    "crd Clearance": {"name": "CRD Clearance Certificate", "essential": True}
}


def check_regulatory_readiness(
    segment: str,
    company_data: Dict,
    parties_appointed: List[str],
    documents_ready: List[str]
) -> Dict:
    """
    Check NSE regulatory readiness for a specific segment.

    Returns:
        {
            "regulatory_score": 0-100,
            "requirements_met": {"total": X, "met": Y, "details": [...]},
            "parties": {"total": 4, "appointed": Z, "details": [...]},
            "documents": {"total": X, "ready": Y, "missing": [...]},
            "timeline_estimate": "X months",
            "quick_wins": [...]
        }
    """
    segment_reqs = NSE_SEGMENT_REQUIREMENTS.get(segment.upper(), NSE_SEGMENT_REQUIREMENTS["GEMS"])
    requirements = segment_reqs["requirements"]

    # Check numeric requirements
    req_results = []
    req_met = 0
    req_total = 0

    # Issued Share Capital
    issued_cap = company_data.get("issued_share_capital", 0)
    cap_req = requirements["issued_share_capital"]
    req_total += 1
    cap_status = "✓ Met" if issued_cap >= cap_req["min"] else "❌ Below"
    if issued_cap >= cap_req["min"]:
        req_met += 1
    req_results.append({
        "requirement": cap_req["name"],
        "required": f"{cap_req['min']:,} {cap_req['unit']}",
        "actual": f"{issued_cap:,} KES",
        "status": "met" if issued_cap >= cap_req["min"] else "below",
        "display": f"{cap_req['name']}: {cap_status}"
    })

    # Shareholders
    shareholders = company_data.get("shareholders_count", 0)
    shareholders_req = requirements["shareholders"]
    req_total += 1
    shareholder_status = "✓ Met" if shareholders >= shareholders_req["min"] else "❌ Below"
    if shareholders >= shareholders_req["min"]:
        req_met += 1
    req_results.append({
        "requirement": shareholders_req["name"],
        "required": f"{shareholders_req['min']:,}",
        "actual": str(shareholders),
        "status": "met" if shareholders >= shareholders_req["min"] else "below",
        "display": f"{shareholders_req['name']}: {shareholder_status}"
    })

    # Free Float
    free_float = company_data.get("free_float_percent", 0)
    float_req = requirements["free_float"]
    req_total += 1
    float_status = "✓ Met" if free_float >= float_req["min"] else "❌ Below"
    if free_float >= float_req["min"]:
        req_met += 1
    req_results.append({
        "requirement": float_req["name"],
        "required": f"{float_req['min']}%",
        "actual": f"{free_float}%",
        "status": "met" if free_float >= float_req["min"] else "below",
        "display": f"{float_req['name']}: {float_status}"
    })

    # Trading Years
    trading_years = company_data.get("trading_years", 0)
    trading_req = requirements["trading_years"]
    req_total += 1
    if trading_years >= trading_req["min"]:
        req_met += 1
        trading_status = "✓ Met"
    elif trading_req.get("waiver_possible") and trading_years >= 1:
        trading_status = "⚠️ Waiver needed"
    else:
        trading_status = "❌ Below"
    req_results.append({
        "requirement": trading_req["name"],
        "required": f"{trading_req['min']}+ years",
        "actual": f"{trading_years} years",
        "status": "met" if trading_years >= trading_req["min"] else "waiver_possible" if trading_req.get("waiver_possible") and trading_years >= 1 else "below",
        "display": f"{trading_req['name']}: {trading_status}"
    })

    # Check Key Parties
    essential_parties = [k for k, v in KEY_PARTIES.items() if v["essential"]]
    parties_appointed_lower = [p.lower().replace("-", "_") for p in parties_appointed]
    parties_total = len(essential_parties)
    parties_met = sum(1 for p in essential_parties if p in parties_appointed_lower)
    parties_details = []
    for party_key in essential_parties:
        party_info = KEY_PARTIES[party_key]
        is_appointed = party_key in parties_appointed_lower
        parties_details.append({
            "name": party_info["name"],
            "appointed": is_appointed,
            "essential": True,
            "description": party_info["description"]
        })

    # Check Documents
    all_docs = REQUIRED_DOCUMENTS
    essential_docs = [k for k, v in all_docs.items() if v["essential"]]
    docs_ready_lower = [d.lower().replace("-", "_") for d in documents_ready]
    docs_total = len(essential_docs)
    docs_met = sum(1 for d in essential_docs if d in docs_ready_lower)
    documents_details = []
    missing_docs = []
    for doc_key in essential_docs:
        doc_info = all_docs[doc_key]
        is_ready = doc_key in docs_ready_lower
        documents_details.append({
            "name": doc_info["name"],
            "ready": is_ready,
            "essential": True
        })
        if not is_ready:
            missing_docs.append(doc_info["name"])

    # Calculate regulatory score
    regulatory_score = int(((req_met / req_total) * 40 + (parties_met / parties_total) * 30 + (docs_met / docs_total) * 30))

    # Generate quick wins
    quick_wins = []
    if parties_met < parties_total:
        missing_parties = [KEY_PARTIES[p]["name"] for p in essential_parties if p not in parties_appointed_lower]
        quick_wins.append(f"Appoint missing parties: {', '.join(missing_parties)}")
    if docs_met < docs_total:
        if len(missing_docs) <= 3:
            quick_wins.append(f"Prepare missing documents: {', '.join(missing_docs[:3])}")
    if free_float < float_req["min"]:
        quick_wins.append(f"Increase free float from {free_float}% to {float_req['min']}%")
    if shareholders < shareholders_req["min"]:
        needed = shareholders_req["min"] - shareholders
        quick_wins.append(f"Get {needed} more shareholders (consider ESOP)")
    if issued_cap < cap_req["min"]:
        needed_cap = (cap_req["min"] - issued_cap) / 1_000_000
        quick_wins.append(f"Increase share capital by KES {needed_cap:.0f}M")

    # Estimate timeline
    remaining_items = (req_total - req_met) + (parties_total - parties_met) + (docs_total - docs_met)
    if remaining_items <= 2:
        timeline = "2-3 months"
    elif remaining_items <= 5:
        timeline = "4-6 months"
    elif remaining_items <= 8:
        timeline = "6-9 months"
    else:
        timeline = "9-12 months"

    return {
        "regulatory_score": regulatory_score,
        "requirements": {
            "total": req_total,
            "met": req_met,
            "results": req_results
        },
        "parties": {
            "total": parties_total,
            "appointed": parties_met,
            "details": parties_details
        },
        "documents": {
            "total": docs_total,
            "ready": docs_met,
            "details": documents_details,
            "missing": missing_docs
        },
        "timeline_estimate": timeline,
        "quick_wins": quick_wins
    }


def generate_combined_recommendation(
    regulatory_score: int,
    company_health_score: int,
    segment: str
) -> str:
    """Generate a combined recommendation considering both scores."""

    if regulatory_score >= 80 and company_health_score >= 70:
        return f"Excellent position for {segment} listing. Strong fundamentals and regulatory readiness. Focus on prospectus preparation and CMA engagement."
    elif regulatory_score >= 60 and company_health_score >= 60:
        return f"Good progress toward {segment} listing. Address the identified gaps within 3-6 months for optimal timing."
    elif regulatory_score < 40 and company_health_score >= 70:
        return f"Your fundamentals are solid ({company_health_score}/100), but you're not regulatorily ready ({regulatory_score}%). Focus on: appointing key parties and meeting {segment} thresholds before engaging CMA."
    elif regulatory_score >= 60 and company_health_score < 50:
        return f"You're regulatorily prepared but company fundamentals need work ({company_health_score}/100). Consider strengthening governance and financial track record before listing."
    else:
        return f"Significant work needed on both regulatory readiness ({regulatory_score}%) and company fundamentals ({company_health_score}/100). Estimated timeline: 9-12 months."
