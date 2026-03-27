"""
Document Verification Service
Uses Claude API to verify uploaded documents for listing readiness.

This replaces the misleading "public cross-check" approach with REAL document verification.
"""

import os
import json
from typing import Dict, List, Optional
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DOCUMENT_VERIFICATION_PROMPT = """You are a document verification expert for Nairobi Securities Exchange (NSE) listings.

Analyze the provided document content and verify:

1. **Document Type**: What kind of document is this? (Audited Financials, Tax Compliance, Board Resolution, CRD Certificate, etc.)

2. **Issuing Authority**: Who issued this document? (Auditor firm name, KRA, Company Secretary, CRD, etc.)

3. **Key Information Extracted**: What are the important details?
   - For financials: Revenue, profit, assets, auditor name, audit opinion
   - For tax cert: KRA PIN, tax period, compliance status
   - For board resolution: Date, resolution details, directors present
   - For CRD: Reference number, company registration details

4. **Validity Indicators**: Signs this is authentic
   - Official letterhead/logo
   - Signature(s)
   - Date
   - Reference number
   - Official seal/stamp

5. **Red Flags**: Any concerning signs
   - Incomplete information
   - Expired dates
   - Missing signatures
   - Inconsistent information
   - Unusual formatting

6. **Verification Confidence**: High/Medium/Low - how confident are you in this verification?

Return ONLY valid JSON in this exact format:
{
  "document_type": "Audited Financial Statements",
  "issuing_authority": "KPMG Kenya",
  "key_info": {
    "revenue": "KES 15.2M",
    "audit_opinion": "Unqualified",
    "audit_date": "2024-12-31"
  },
  "validity_indicators": ["Official letterhead", "Auditor signature", "Date present"],
  "red_flags": [],
  "confidence": "High",
  "verification_score": 8
}
"""


async def verify_uploaded_document(
    file_path: str,
    document_type: str,
    company_name: str
) -> Dict:
    """
    Verify a single uploaded document using Claude API.

    Args:
        file_path: Path to uploaded file (PDF or image)
        document_type: Expected document type
        company_name: Name of company being verified

    Returns:
        {
            "document_type": "...",
            "issuing_authority": "...",
            "key_info": {...},
            "validity_indicators": [...],
            "red_flags": [...],
            "confidence": "High/Medium/Low",
            "verification_score": 0-10,
            "file_name": "...",
            "file_size": 12345,
            "verification_method": "Claude AI document analysis"
        }
    """
    # Extract text from file
    text_content = await extract_document_text(file_path)

    if not text_content or len(text_content.strip()) < 50:
        return {
            "document_type": document_type,
            "verification_score": 0,
            "confidence": "Low",
            "red_flags": ["Could not extract meaningful text from document"],
            "key_info": {},
            "validity_indicators": [],
            "issuing_authority": "Unknown",
            "error": "Document text extraction failed"
        }

    # Limit text content for API (first 15000 chars)
    text_preview = text_content[:15000]

    # Call Claude API for verification
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": f"{DOCUMENT_VERIFICATION_PROMPT}\n\nDocument Type Expected: {document_type}\nCompany Name: {company_name}\n\nDocument Content:\n{text_preview}"
            }]
        )

        response_text = message.content[0].text
        result = json.loads(response_text)

        # Add metadata
        result["file_name"] = os.path.basename(file_path)
        result["file_size"] = os.path.getsize(file_path)
        result["verification_method"] = "Claude AI document analysis"

        return result

    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        return {
            "document_type": document_type,
            "verification_score": 3,
            "confidence": "Low",
            "red_flags": ["Failed to parse document structure"],
            "key_info": {},
            "validity_indicators": [],
            "issuing_authority": "Unknown",
            "error": "Document analysis failed"
        }
    except Exception as e:
        return {
            "document_type": document_type,
            "verification_score": 0,
            "confidence": "Low",
            "red_flags": [f"Verification error: {str(e)}"],
            "key_info": {},
            "validity_indicators": [],
            "issuing_authority": "Unknown",
            "error": str(e)
        }


async def extract_document_text(file_path: str) -> str:
    """Extract text from PDF or image file."""
    import PyPDF2

    if file_path.endswith('.pdf'):
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    try:
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                    except Exception:
                        continue
            return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    else:
        # For images, we'd need pytesseract OCR
        # For now, return a placeholder
        return f"[Image file - OCR not implemented for {file_path}]"


async def verify_manual_codes(
    auditor_contact: Optional[str] = None,
    kra_pin: Optional[str] = None,
    crd_reference: Optional[str] = None
) -> Dict:
    """
    Verify manually entered codes using basic validation.
    This provides basic validation without full document upload.
    """
    results = {}
    overall_score = 0
    max_score = 0

    if auditor_contact:
        max_score += 3
        # Basic email/phone validation
        is_valid = (
            "@" in auditor_contact or  # Email
            any(c.isdigit() for c in auditor_contact)  # Has digits (phone)
        )
        if is_valid:
            results["auditor_contact"] = {
                "provided": auditor_contact,
                "valid": True,
                "verification_score": 2
            }
            overall_score += 2
        else:
            results["auditor_contact"] = {
                "provided": auditor_contact,
                "valid": False,
                "verification_score": 0
            }

    if kra_pin:
        max_score += 4
        # KRA PIN format: A00... (starts with letter, 11 digits)
        is_valid = (
            len(kra_pin) == 11 and
            kra_pin[0].isalpha() and
            kra_pin[1:].isdigit()
        )
        if is_valid:
            results["kra_pin"] = {
                "provided": kra_pin[:4] + "*******",  # Masked
                "valid": True,
                "verification_score": 4
            }
            overall_score += 4
        else:
            results["kra_pin"] = {
                "provided": kra_pin,
                "valid": False,
                "verification_score": 0
            }

    if crd_reference:
        max_score += 3
        # CRD reference should be alphanumeric, 6+ chars
        is_valid = len(crd_reference) >= 6 and crd_reference.replace("-", "").replace("/", "").isalnum()
        if is_valid:
            results["crd_reference"] = {
                "provided": crd_reference[:4] + "*******",  # Masked
                "valid": True,
                "verification_score": 3
            }
            overall_score += 3
        else:
            results["crd_reference"] = {
                "provided": crd_reference,
                "valid": False,
                "verification_score": 0
            }

    return {
        "results": results,
        "overall_score": overall_score,
        "max_score": max_score,
        "verification_method": "Manual code validation",
        "entries_provided": sum(1 for v in results.values() if v.get("provided"))
    }


def get_document_verification_summary(document_verifications: Dict) -> str:
    """
    Generate a human-readable summary of document verification results.
    """
    if not document_verifications:
        return "No documents provided for verification."

    verified_count = sum(
        1 for v in document_verifications.values()
        if v.get("verification_score", 0) >= 5
    )
    total_count = len([v for v in document_verifications.values() if v.get("document_type")])

    if verified_count == 0:
        return f"Documents uploaded but verification failed for all {total_count} documents."

    confidence = sum(
        v.get("verification_score", 0) for v in document_verifications.values()
    ) / max(total_count, 1)

    if confidence >= 7:
        return f"Strong verification: {verified_count}/{total_count} documents verified."
    elif confidence >= 4:
        return f"Moderate verification: {verified_count}/{total_count} documents verified."
    else:
        return f"Weak verification: {verified_count}/{total_count} documents verified."
