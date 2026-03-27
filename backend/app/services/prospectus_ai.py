"""
Prospectus Compliance Checker Service
Uses Claude API to analyze draft prospectuses against CMA requirements
"""

import os
import anthropic
from datetime import datetime
from typing import Dict, List, Optional
import PyPDF2
from io import BytesIO

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# CMA Kenya listing requirements summary for system prompt
CMA_REQUIREMENTS = """
CMA KENYA LISTING RULES - Key Requirements for Prospectus:

1. Financial Information
   - Audited financial statements (minimum 3 years)
   - Balance sheet, income statement, cash flow statement
   - Auditor's report with clean opinion
   - Interim financial statements (if available)

2. Business Overview
   - Company history and operations
   - Management discussion and analysis (MD&A)
   - Industry and competitive landscape
   - Risk factors (market, operational, financial, regulatory)

3. Corporate Governance
   - Board composition (minimum 5 directors, majority independent)
   - Board committees: Audit, Risk, Nominations
   - Executive compensation structure
   - Share ownership structure

4. Offering Details
   - Clear statement of use of proceeds
   - Offering size and pricing methodology
   - Underwriting agreement details
   - Share capital structure pre- and post-offer

5. Legal and Regulatory
   - Certificate of incorporation
   - CMA approval status
   - Material contracts
   - Legal opinion on the offering

6. Risk Factors
   - Market and industry risks
   - Company-specific risks
   - Regulatory risks
   - Financial risks
   - ESG considerations (increasingly important)
"""

PROSPECTUS_ANALYSIS_PROMPT = f"""You are a CMA Kenya compliance expert with deep knowledge of the Capital Markets Act and the CMA Listing Rules.

Your task is to review a draft prospectus and identify compliance gaps.

{CMA_REQUIREMENTS}

ANALYSIS INSTRUCTIONS:
1. Extract text from the prospectus
2. Compare against CMA requirements
3. Identify gaps (missing or insufficient sections)
4. Rate severity: critical (must have), major (significantly incomplete), minor (needs enhancement)
5. Provide specific recommendations for each gap

Return ONLY valid JSON in this exact format:
{{
  "compliance_score": 0-100,
  "sections_reviewed": ["list of sections found"],
  "gaps": [
    {{
      "section": "section name",
      "issue": "description of the gap",
      "severity": "critical/major/minor",
      "recommendation": "specific recommendation to fix"
    }}
  ],
  "missing_sections": ["list of completely missing sections"],
  "overall_recommendation": "summary statement (Ready for review/Needs revision/Significant gaps)"
}}

SCORING GUIDE:
- 90-100: Ready for CMA submission
- 70-89: Minor revisions needed
- 50-69: Major gaps to address
- Below 50: Significant restructuring required
"""


async def analyze_prospectus_compliance(file_path: str) -> Dict:
    """
    Analyze a prospectus PDF against CMA Kenya requirements.

    Args:
        file_path: Path to the PDF file

    Returns:
        Dict with compliance score, gaps, and recommendations
    """
    # Extract text from PDF
    text_content = await extract_pdf_text(file_path)

    if not text_content or len(text_content) < 100:
        return {
            "error": "Could not extract sufficient text from PDF. Please ensure the file is readable.",
            "text_length": len(text_content) if text_content else 0
        }

    # Truncate if too long (Claude has token limits)
    max_chars = 15000  # Leave room for prompt
    if len(text_content) > max_chars:
        text_content = text_content[:max_chars] + "\n\n[Document truncated for analysis...]"

    # Build prompt
    prompt = f"""Analyze the following draft prospectus for CMA Kenya compliance.

PROSPECTUS TEXT:
{text_content}

Please provide the compliance analysis as specified."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2500,
            temperature=0.2,
            system=PROSPECTUS_ANALYSIS_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )

        import json
        response_text = response.content[0].text

        # Extract JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        result = json.loads(response_text)
        result["analyzed_at"] = datetime.utcnow().isoformat()
        result["text_length_analyzed"] = len(text_content)

        return result

    except json.JSONDecodeError as e:
        return {
            "error": "Failed to parse analysis response",
            "raw_response": response_text if 'response_text' in locals() else "No response"
        }
    except Exception as e:
        # If API fails, return demo analysis for testing
        if not os.getenv("ANTHROPIC_API_KEY"):
            return get_demo_prospectus_analysis()
        return {
            "error": f"Analysis failed: {str(e)}",
            "hint": "Ensure ANTHROPIC_API_KEY is set"
        }


async def extract_pdf_text(file_path: str) -> str:
    """Extract text content from a PDF file."""
    try:
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            text_content = ""

            for page in pdf_reader.pages:
                text_content += page.extract_text() + "\n"

            return text_content.strip()
    except Exception as e:
        return ""


def get_demo_prospectus_analysis() -> Dict:
    """Return demo prospectus analysis for testing."""
    return {
        "compliance_score": 65,
        "sections_reviewed": [
            "Business Overview",
            "Financial Information",
            "Offering Details",
            "Risk Factors"
        ],
        "gaps": [
            {
                "section": "Corporate Governance",
                "issue": "Board composition does not meet CMA requirement for majority independent directors",
                "severity": "critical",
                "recommendation": "Add at least 2 independent directors to achieve majority independent board composition"
            },
            {
                "section": "Corporate Governance",
                "issue": "Audit committee details missing - no information on composition or meetings",
                "severity": "major",
                "recommendation": "Add detailed section on audit committee including member names, qualifications, and meeting frequency"
            },
            {
                "section": "Financial Information",
                "issue": "Only 2 years of audited statements provided; CMA requires minimum 3 years",
                "severity": "critical",
                "recommendation": "Include audited financial statements for the third year"
            },
            {
                "section": "Use of Proceeds",
                "issue": "Use of proceeds section lacks specificity - percentages not clearly allocated",
                "severity": "major",
                "recommendation": "Provide detailed breakdown of use of proceeds with specific percentages and timeline"
            },
            {
                "section": "Risk Factors",
                "issue": "ESG risks not addressed - increasingly important for CMA",
                "severity": "minor",
                "recommendation": "Add ESG risk factors including climate risk, social impact, and governance considerations"
            },
            {
                "section": "Legal and Regulatory",
                "issue": "CMA approval status not clearly stated",
                "severity": "major",
                "recommendation": "Add explicit statement on CMA pre-approval status and application reference"
            }
        ],
        "missing_sections": [
            "Board Committee details (Audit, Risk, Nominations)",
            "Share ownership structure pre- and post-offer",
            "Underwriting agreement details",
            "Legal opinion on the offering"
        ],
        "overall_recommendation": "Needs revision - address critical gaps before CMA submission",
        "analyzed_at": datetime.utcnow().isoformat(),
        "note": "This is a demo analysis for testing purposes"
    }
