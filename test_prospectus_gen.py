"""
Generate a test prospectus PDF with intentional CMA compliance gaps
for demonstrating the Prospectus Compliance Checker.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors

def create_test_prospectus(filename="test_prospectus.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        spaceAfter=30,
        alignment=TA_CENTER
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.darkblue,
        spaceAfter=12
    )
    normal_style = styles['Normal']
    normal_style.fontSize = 11

    story = []

    # Title Page
    story.append(Paragraph("PROSPECTUS", title_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Test Tech Limited", ParagraphStyle('Center', parent=styles['Normal'], fontSize=16, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph("Initial Public Offering", ParagraphStyle('Center', parent=styles['Normal'], fontSize=14, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("10,000,000 Ordinary Shares of KES 1.00 Each", ParagraphStyle('Center', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph("Offer Price: KES 10.00 per Share", ParagraphStyle('Center', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph("March 2025", ParagraphStyle('Center', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER, textColor=colors.gray)))
    story.append(PageBreak())

    # Section 1: Business Overview (present but brief)
    story.append(Paragraph("1. BUSINESS OVERVIEW", heading_style))
    story.append(Paragraph(
        "Test Tech Limited is a Kenyan technology company founded in 2020. "
        "We provide software solutions for small businesses in East Africa. "
        "Our main product is a point-of-sale system that helps merchants manage inventory, "
        "process payments, and track sales analytics.",
        normal_style
    ))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "<b>Management Discussion:</b> The company has grown steadily since inception. "
        "We have over 500 active customers across Kenya, Uganda, and Tanzania.",
        normal_style
    ))
    story.append(Spacer(1, 0.2*inch))

    # Section 2: Financial Information (INTENTIONAL GAP: only 2 years, not 3)
    story.append(Paragraph("2. FINANCIAL INFORMATION", heading_style))
    story.append(Paragraph(
        "<b>Selected Financial Data (KES Millions):</b>",
        normal_style
    ))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "Year Ended December 31, 2024: Revenue KES 450M, Net Profit KES 85M<br/>"
        "Year Ended December 31, 2023: Revenue KES 320M, Net Profit KES 52M",
        normal_style
    ))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "<i>Note: Financial statements have been audited by KPMG Kenya.</i>",
        normal_style
    ))
    story.append(Spacer(1, 0.2*inch))

    # Section 3: Corporate Governance (INTENTIONAL GAP: only 2 directors, not enough)
    story.append(Paragraph("3. CORPORATE GOVERNANCE", heading_style))
    story.append(Paragraph(
        "<b>Board of Directors:</b>",
        normal_style
    ))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "1. John Kamau — Chairman and Executive Director<br/>"
        "2. Mary Wanjiku — CEO and Executive Director",
        normal_style
    ))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "<b>Board Committees:</b> The board has established an Audit Committee. "
        "Details on committee composition and meeting frequency will be provided.",
        normal_style
    ))
    story.append(Spacer(1, 0.2*inch))

    # Section 4: Offering Details (INTENTIONAL GAP: vague use of proceeds)
    story.append(Paragraph("4. OFFERING DETAILS", heading_style))
    story.append(Paragraph(
        f"<b>Offering Size:</b> 10,000,000 shares at KES 10.00 per share = KES 100 Million",
        normal_style
    ))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "<b>Use of Proceeds:</b> The net proceeds from this offering will be used for: "
        "business expansion, working capital, and general corporate purposes.",
        normal_style
    ))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "<b>Pricing Methodology:</b> The offer price was determined based on "
        "market conditions and peer valuation.",
        normal_style
    ))
    story.append(Spacer(1, 0.2*inch))

    # Section 5: Risk Factors (INTENTIONAL GAP: no ESG risks mentioned)
    story.append(Paragraph("5. RISK FACTORS", heading_style))
    story.append(Paragraph(
        "<b>Market Risks:</b> Our business is subject to economic conditions in East Africa. "
        "A downturn could affect our growth prospects.",
        normal_style
    ))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "<b>Operational Risks:</b> We depend on key personnel. Loss of key personnel "
        "could adversely affect our business.",
        normal_style
    ))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "<b>Financial Risks:</b> We have a significant amount of debt. "
        "Our ability to service this debt depends on our cash flow.",
        normal_style
    ))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "<b>Regulatory Risks:</b> Changes in technology regulations could impact our business.",
        normal_style
    ))
    story.append(Spacer(1, 0.2*inch))

    # Section 6: Legal and Regulatory (INTENTIONAL GAP: no CMA approval status)
    story.append(Paragraph("6. LEGAL AND REGULATORY", heading_style))
    story.append(Paragraph(
        "<b>Company Registration:</b> Test Tech Limited is incorporated in Kenya "
        "under the Companies Act, 2015. Certificate of Incorporation: PVT-ABC12345",
        normal_style
    ))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "<b>Material Contracts:</b> We have entered into significant customer contracts. "
        "Details available on request.",
        normal_style
    ))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph(
        "<b>Legal Opinion:</b> Legal opinion regarding the offering will be provided.",
        normal_style
    ))
    story.append(Spacer(1, 0.2*inch))

    # Disclaimer
    story.append(PageBreak())
    story.append(Paragraph(
        "<b>IMPORTANT DISCLAIMER:</b><br/><br/>"
        "This is a TEST PROSPECTUS generated for demonstration purposes only.<br/>"
        "It does not represent a real company or a real offering.<br/>"
        "This prospectus contains INTENTIONAL COMPLIANCE GAPS to demonstrate "
        "the Hazina Prospectus Compliance Checker functionality.",
        ParagraphStyle('Disclaimer', parent=styles['Normal'], fontSize=9, textColor=colors.red, fontName='Helvetica-Oblique')
    ))

    doc.build(story)
    print(f"✅ Test prospectus created: {filename}")
    print("\nIntentional gaps included:")
    print("  🔴 CRITICAL: Only 2 years of financials (CMA requires 3)")
    print("  🔴 CRITICAL: Only 2 directors, both executive (need 5+ with majority independent)")
    print("  🟡 MAJOR: Use of proceeds is vague (no percentages or breakdown)")
    print("  🟡 MAJOR: No CMA approval status mentioned")
    print("  🔵 MINOR: No ESG risks in risk factors")

if __name__ == "__main__":
    create_test_prospectus("test_prospectus.pdf")
