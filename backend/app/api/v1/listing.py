"""
Listing Readiness Scanner endpoints
6-dimension scoring for companies considering NSE listing
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import json

from app.db.database import get_db, ListingScore
from app.services.listing_scorer import analyze_company_readiness, analyze_company_readiness_hybrid, NSE_SEGMENT_REQUIREMENTS
from app.services.verifier import cross_check_company_data, get_demo_verification
from app.services import document_verifier
import tempfile
import os

router = APIRouter()


class ListingRequest(BaseModel):
    company_name: str
    symbol: Optional[str] = None
    force_refresh: bool = False  # Re-analyze even if cached


@router.post("/scan")
async def scan_company(
    request: ListingRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze a company's listing readiness across 6 dimensions.

    Dimensions scored (0-10 each):
    - Revenue: Turnover stability, growth trajectory
    - Governance: Board composition, audit quality
    - Growth: Market opportunity, competitive position
    - Compliance: Regulatory filings, tax compliance
    - Market Size: TAM, sector comparables
    - Timing: Market conditions, sector cycle

    Returns overall score 0-100 with recommendation.
    """
    company_name = request.company_name.strip()
    symbol = request.symbol.upper() if request.symbol else None

    # Check if we have a recent analysis (less than 7 days old)
    if not request.force_refresh:
        from datetime import timedelta
        from app.db.database import ListingScore
        cutoff_time = datetime.utcnow() - timedelta(days=7)

        query = select(ListingScore).where(
            and_(
                ListingScore.company_name == company_name,
                ListingScore.created_at >= cutoff_time
            )
        )
        result = await db.execute(query)
        cached = result.scalar_one_or_none()

        if cached:
            return _format_score_response(cached, cached=True)

    # Run new analysis
    result = await analyze_company_readiness(company_name, symbol)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Save to database
    new_score = ListingScore(
        company_name=company_name,
        symbol=symbol,
        revenue_score=result["scores"]["revenue"],
        governance_score=result["scores"]["governance"],
        growth_score=result["scores"]["growth"],
        compliance_score=result["scores"]["compliance"],
        market_size_score=result["scores"]["market_size"],
        timing_score=result["scores"]["timing"],
        overall_score=result["overall_score"],
        recommendation=result["recommendation"],
        revenue_breakdown=result["breakdowns"]["revenue"],
        governance_breakdown=result["breakdowns"]["governance"],
        growth_breakdown=result["breakdowns"]["growth"],
        compliance_breakdown=result["breakdowns"]["compliance"],
        market_size_breakdown=result["breakdowns"]["market_size"],
        timing_breakdown=result["breakdowns"]["timing"],
        data_sources=result.get("data_sources", []),
        overall_confidence=result.get("confidence", "Medium")
    )

    db.add(new_score)
    await db.commit()
    await db.refresh(new_score)

    return _format_score_response(new_score, cached=False)


def _format_score_response(score: ListingScore, cached: bool = False) -> dict:
    """Format a ListingScore for API response."""
    return {
        "company": score.company_name,
        "symbol": score.symbol,
        "overall_score": score.overall_score,
        "recommendation": score.recommendation,
        "confidence": score.overall_confidence,
        "cached": cached,
        "dimensions": {
            "revenue": {
                "score": score.revenue_score,
                "breakdown": score.revenue_breakdown
            },
            "governance": {
                "score": score.governance_score,
                "breakdown": score.governance_breakdown
            },
            "growth": {
                "score": score.growth_score,
                "breakdown": score.growth_breakdown
            },
            "compliance": {
                "score": score.compliance_score,
                "breakdown": score.compliance_breakdown
            },
            "market_size": {
                "score": score.market_size_score,
                "breakdown": score.market_size_breakdown
            },
            "timing": {
                "score": score.timing_score,
                "breakdown": score.timing_breakdown
            }
        },
        "data_sources": score.data_sources,
        "analyzed_at": score.created_at.isoformat(),
        "note": "Scores based on publicly available information. Not financial advice."
    }


@router.get("/companies")
async def get_scanned_companies(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of companies that have been scanned.
    """
    from sqlalchemy import desc
    from app.db.database import ListingScore

    query = (
        select(ListingScore)
        .order_by(desc(ListingScore.created_at))
        .limit(limit)
    )

    result = await db.execute(query)
    scores = result.scalars().all()

    return {
        "companies": [
            {
                "name": s.company_name,
                "symbol": s.symbol,
                "overall_score": s.overall_score,
                "recommendation": s.recommendation,
                "analyzed_at": s.created_at.isoformat()
            }
            for s in scores
        ]
    }


@router.post("/analyze-hybrid")
async def analyze_hybrid(
    background_tasks: BackgroundTasks,
    company_name: str = Form(...),
    sector: str = Form(...),
    segment: str = Form("GEMS"),
    website: Optional[str] = Form(None),
    issued_share_capital: Optional[int] = Form(0),
    shareholders_count: Optional[int] = Form(0),
    free_float_percent: Optional[int] = Form(0),
    trading_years: Optional[float] = Form(0),
    revenue_history_json: Optional[str] = Form(None),
    board_members_json: Optional[str] = Form(None),
    tax_compliant: bool = Form(True),
    licenses_json: Optional[str] = Form(None),
    litigation: Optional[str] = Form(None),
    key_parties_json: Optional[str] = Form("[]"),
    documents_ready_json: Optional[str] = Form("[]"),
    # NEW: Document uploads for real verification
    financials_file: Optional[UploadFile] = File(None),
    tax_cert_file: Optional[UploadFile] = File(None),
    board_resolution_file: Optional[UploadFile] = File(None),
    crd_cert_file: Optional[UploadFile] = File(None),
    # NEW: Manual verification codes
    auditor_contact: Optional[str] = Form(None),
    kra_pin: Optional[str] = Form(None),
    crd_reference: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Enhanced NSE Listing Readiness Analysis.

    Combines:
    1. Company Health (6-dimension scoring) — "Should we list?"
    2. Regulatory Readiness (NSE segment requirements) — "Can we list?"
    3. Document Verification (optional) — Real verification from uploaded docs

    Form fields:
    - company_name: Company name (required)
    - sector: Business sector (required)
    - segment: NSE segment - GEMS, AIMS, or MIMS (default: GEMS)
    - website: Company website URL (optional)
    - issued_share_capital: Issued share capital in KES (optional)
    - shareholders_count: Number of shareholders (optional)
    - free_float_percent: Free float percentage (optional)
    - trading_years: Years of trading history (optional)
    - revenue_history_json: JSON string of {year: revenue} (optional)
    - board_members_json: JSON string of board members (optional)
    - tax_compliant: Boolean for tax compliance status (default: true)
    - licenses_json: JSON string of license numbers (optional)
    - litigation: Description of active litigation (optional)
    - key_parties_json: JSON array of appointed parties (optional)
    - documents_ready_json: JSON array of ready documents (optional)

    Document Uploads (NEW):
    - financials_file: Audited financial statements PDF/image
    - tax_cert_file: Tax compliance certificate PDF/image
    - board_resolution_file: Board resolution PDF/image
    - crd_cert_file: CRD clearance certificate PDF/image

    Manual Verification (NEW):
    - auditor_contact: Auditor email or phone number
    - kra_pin: KRA Tax PIN (format: A00xxxxxxxx)
    - crd_reference: CRD reference number

    Returns:
        Enhanced analysis with both company health and regulatory readiness scores.
    """
    company_name = company_name.strip()

    # Parse JSON fields
    try:
        revenue_history = json.loads(revenue_history_json) if revenue_history_json else {}
    except json.JSONDecodeError:
        revenue_history = {}

    try:
        board_members = json.loads(board_members_json) if board_members_json else []
    except json.JSONDecodeError:
        board_members = []

    try:
        licenses = json.loads(licenses_json) if licenses_json else []
    except json.JSONDecodeError:
        licenses = []

    try:
        key_parties = json.loads(key_parties_json) if key_parties_json else []
    except json.JSONDecodeError:
        key_parties = []

    try:
        documents_ready = json.loads(documents_ready_json) if documents_ready_json else []
    except json.JSONDecodeError:
        documents_ready = []

    # ===== NEW: Document Upload Verification =====
    document_verification = {}
    uploaded_files = {
        "financials": financials_file,
        "tax_cert": tax_cert_file,
        "board_resolution": board_resolution_file,
        "crd_cert": crd_cert_file
    }

    for doc_type, file in uploaded_files.items():
        if file and file.filename:
            try:
                # Save uploaded file to temp location
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix=f"_{file.filename}"
                )
                content = await file.read()
                temp_file.write(content)
                temp_file.close()

                # Verify document using Claude API
                doc_labels = {
                    "financials": "Audited Financial Statements",
                    "tax_cert": "Tax Compliance Certificate",
                    "board_resolution": "Board Resolution",
                    "crd_cert": "CRD Clearance Certificate"
                }

                verification_result = await document_verifier.verify_uploaded_document(
                    temp_file.name,
                    doc_labels[doc_type],
                    company_name
                )

                document_verification[doc_type] = verification_result

                # Clean up temp file
                try:
                    os.unlink(temp_file.name)
                except Exception:
                    pass  # Best effort cleanup

            except Exception as e:
                document_verification[doc_type] = {
                    "document_type": doc_type,
                    "verification_score": 0,
                    "confidence": "Low",
                    "red_flags": [f"Verification failed: {str(e)}"],
                    "key_info": {},
                    "validity_indicators": [],
                    "issuing_authority": "Unknown",
                    "error": str(e)
                }

    # ===== NEW: Manual Code Verification =====
    manual_verification = {}
    if any([auditor_contact, kra_pin, crd_reference]):
        manual_result = await document_verifier.verify_manual_codes(
            auditor_contact=auditor_contact,
            kra_pin=kra_pin,
            crd_reference=crd_reference
        )
        manual_verification = manual_result

    # Build company input dict
    company_input = {
        "name": company_name,
        "sector": sector,
        "segment": segment,
        "website": website,
        "issued_share_capital": issued_share_capital or 0,
        "shareholders_count": shareholders_count or 0,
        "free_float_percent": free_float_percent or 0,
        "trading_years": trading_years or 0,
        "revenue_history": revenue_history,
        "board_members": board_members,
        "tax_compliant": tax_compliant,
        "licenses": licenses,
        "litigation": litigation,
        "key_parties": key_parties,
        "documents_ready": documents_ready
    }

    # Run verification against public sources
    try:
        verification = await cross_check_company_data(company_name, company_input)
    except Exception as e:
        # Fallback to demo verification for demo companies
        demo_verification = await get_demo_verification(company_name)
        if demo_verification:
            verification = demo_verification
        else:
            verification = {
                "confirmations": [],
                "discrepancies": [],
                "red_flags": [],
                "trust_score": 0.5,
                "sources_used": [],
                "error": str(e)
            }

    # Run enhanced scoring with document verification
    result = await analyze_company_readiness_hybrid(
        company_input,
        verification,
        document_verification=document_verification if document_verification else None,
        manual_verification=manual_verification if manual_verification else None
    )

    # Format response with both company health and regulatory readiness
    company_health = result["company_health"]
    regulatory = result["regulatory_readiness"]

    return {
        "company": company_name,
        "segment": segment,
        "segment_name": NSE_SEGMENT_REQUIREMENTS.get(segment.upper(), NSE_SEGMENT_REQUIREMENTS["GEMS"])["name"],
        # Company Health (6 dimensions)
        "company_health": {
            "overall_score": company_health["overall_score"],
            "recommendation": company_health["recommendation"],
            "dimensions": {
                dim: {
                    "score": score,
                    "breakdown": company_health["breakdowns"][dim]
                }
                for dim, score in company_health["scores"].items()
            }
        },
        # Regulatory Readiness (NSE-specific)
        "regulatory_readiness": {
            "overall_score": regulatory["regulatory_score"],
            "requirements": regulatory["requirements"],
            "key_parties": {
                "appointed": regulatory["parties"]["appointed"],
                "total": regulatory["parties"]["total"],
                "details": regulatory["parties"]["details"]
            },
            "documents": {
                "ready": regulatory["documents"]["ready"],
                "total": regulatory["documents"]["total"],
                "missing": regulatory["documents"]["missing"],
                "details": regulatory["documents"]["details"]
            },
            "timeline_estimate": regulatory["timeline_estimate"],
            "quick_wins": regulatory["quick_wins"]
        },
        # Combined recommendation
        "combined_recommendation": result["combined_recommendation"],
        # Verification data
        "verification": result["verification"],
        # NEW: Document verification results
        "document_verification": document_verification,
        "manual_verification": manual_verification,
        # Metadata
        "analyzed_at": datetime.utcnow().isoformat(),
        "note": "Scores based on company input and NSE segment requirements. Not financial advice."
    }
