"""
Prospectus Compliance Checker endpoints
AI-powered CMA compliance analysis for draft prospectuses
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Optional
import os

from app.db.database import get_db
from app.services.prospectus_ai import analyze_prospectus_compliance

router = APIRouter()

# Max file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Allowed file types
ALLOWED_EXTENSIONS = {".pdf"}

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ComplianceGap(BaseModel):
    section: str
    issue: str
    severity: str  # critical, major, minor
    recommendation: str


class ComplianceReport(BaseModel):
    compliance_score: int  # 0-100
    sections_reviewed: List[str]
    gaps: List[ComplianceGap]
    missing_sections: List[str]
    overall_recommendation: str
    cma_reference: str


@router.post("/check")
async def check_prospectus(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Upload a draft prospectus PDF and get CMA compliance analysis.

    Returns:
    - Compliance score (0-100)
    - List of compliance gaps grouped by severity
    - Missing sections
    - Recommendations for each gap

    PDF is processed using Claude API with CMA Kenya listing requirements.
    """
    # Validate file
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted. Please upload a .pdf file."
        )

    # Check file size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB."
        )

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Save uploaded file
    file_path = os.path.join(UPLOAD_DIR, f"{file.filename}")

    try:
        with open(file_path, "wb") as f:
            f.write(content)

        # Analyze compliance
        result = await analyze_prospectus_compliance(file_path)

        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        return {
            "filename": file.filename,
            "compliance_score": result["compliance_score"],
            "sections_reviewed": result["sections_reviewed"],
            "gaps": result["gaps"],
            "missing_sections": result["missing_sections"],
            "overall_recommendation": result["overall_recommendation"],
            "cma_reference": "CMA Kenya Listing Rules - https://www.cma.or.ke/index.php/regulatory-framework/listing-rules",
            "disclaimer": "This is an AI-assisted review. Not a substitute for professional legal advice.",
            "analyzed_at": result.get("analyzed_at")
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing prospectus: {str(e)}"
        )
    finally:
        # Clean up uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)


@router.get("/requirements")
async def get_cma_requirements():
    """
    Get the CMA Kenya listing requirements structure.
    Returns the framework used for compliance checking.
    """
    return {
        "source": "Capital Markets Authority (CMA) Kenya",
        "reference": "CMA Listing Rules and Requirements",
        "url": "https://www.cma.or.ke/index.php/regulatory-framework/listing-rules",
        "key_sections": [
            {
                "section": "Financial Information",
                "requirements": [
                    "Audited financial statements (minimum 3 years)",
                    "Interim financial statements",
                    "Balance sheet, income statement, cash flow statement",
                    "Auditor's report and opinion"
                ]
            },
            {
                "section": "Business Overview",
                "requirements": [
                    "Company history and operations",
                    "Management discussion and analysis",
                    "Industry and competitive landscape",
                    "Risk factors"
                ]
            },
            {
                "section": "Corporate Governance",
                "requirements": [
                    "Board composition and biographies",
                    "Board committees (audit, risk, nominations)",
                    "Executive compensation",
                    "Share ownership structure"
                ]
            },
            {
                "section": "Offering Details",
                "requirements": [
                    "Use of proceeds",
                    "Offering size and pricing methodology",
                    "Underwriting agreement",
                    "Share capital structure"
                ]
            },
            {
                "section": "Legal and Regulatory",
                "requirements": [
                    "Company registration documents",
                    "CMA approval status",
                    "Material contracts",
                    "Legal opinion on offering"
                ]
            },
            {
                "section": "Risk Factors",
                "requirements": [
                    "Market and industry risks",
                    "Company-specific risks",
                    "Regulatory risks",
                    "Financial risks"
                ]
            }
        ],
        "note": "Full requirements available in CMA Kenya Listing Rules document"
    }
