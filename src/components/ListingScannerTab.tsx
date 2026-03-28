import { useState } from "react";
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer } from "recharts";
import DocumentUpload from "./DocumentUpload";
import { API_BASE } from "../config/api";

// Types
interface FormData {
  company_name: string;
  sector: string;
  segment: "GEMS" | "AIMS" | "MIMS";
  website: string;
  issued_share_capital: string;
  shareholders_count: string;
  free_float_percent: string;
  trading_years: string;
  revenue_years_count: string;
  revenue_year_1: string;
  revenue_year_2: string;
  revenue_year_3: string;
  tax_compliant: boolean;
  litigation: string;
  board_members: Array<{ name: string; role: string; independent: boolean }>;
  key_parties: string[];
  documents_ready: string[];
  [key: string]: string | boolean | string[] | Array<{ name: string; role: string; independent: boolean }>;
}

interface SegmentsType {
  GEMS: { name: string; description: string; source: string; requirements: Array<{ req: string; icon: string }> };
  AIMS: { name: string; description: string; source: string; requirements: Array<{ req: string; icon: string }> };
  MIMS: { name: string; description: string; source: string; requirements: Array<{ req: string; icon: string }> };
  [key: string]: { name: string; description: string; source: string; requirements: Array<{ req: string; icon: string }> };
}

// Theme colors matching HazinaDemo.tsx
const C = {
  bg: "#060B18",
  card: "#0D1425",
  cardAlt: "#111D33",
  border: "#1A2744",
  accent: "#10B981",
  accentDim: "#065F46",
  blue: "#3B82F6",
  blueDim: "#1E3A5F",
  gold: "#F59E0B",
  red: "#EF4444",
  purple: "#8B5CF6",
  cyan: "#06B6D4",
  text: "#F1F5F9",
  textDim: "#94A3B8",
  textMuted: "#64748B",
  warning: "#F59E0B",
};

// Step definitions for navigation
const STEPS = [
  { number: 1, label: "Segment", sublabel: "Choose NSE segment" },
  { number: 2, label: "Company Info", sublabel: "Basic details & requirements" },
  { number: 3, label: "Parties", sublabel: "Key parties appointed" },
  { number: 4, label: "Documents", sublabel: "Document readiness" },
  { number: 5, label: "Verify", sublabel: "Upload for verification" },
  { number: 6, label: "Review", sublabel: "Review & submit" },
];

const font = "'Segoe UI', system-ui, sans-serif";

// Step Navigation Component
const StepNav = ({ currentStep, onStepClick, result }: { currentStep: number; onStepClick: (step: number) => void; result: any }) => {
  // Map current step to nav index
  const getNavIndex = () => {
    if (currentStep === 1) return 0;
    if (currentStep === 2) return 1;
    if (currentStep === 3) return 2;
    if (currentStep === 3.1) return 3;
    if (currentStep === 3.2) return 4;
    if (currentStep === 4) return 5;
    if (currentStep === 5) return 6;
    return 0;
  };

  const currentIndex = getNavIndex();

  // Maximum accessible step (can go back to any visited step)
  const maxAccessibleStep = result ? 6 : currentIndex;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20, padding: "12px 16px", background: C.card, borderRadius: 10, border: `1px solid ${C.border}` }}>
      {STEPS.map((step, index) => {
        const isAccessible = index <= maxAccessibleStep;
        const isActive = index === currentIndex;
        const isPast = index < currentIndex;

        return (
          <div key={step.number} style={{ display: "flex", alignItems: "center", flex: 1 }}>
            <div
              onClick={() => {
                // Map nav index back to actual step
                const stepMap = [1, 2, 3, 3.1, 3.2, 4, 5];
                isAccessible && onStepClick(stepMap[index]);
              }}
              style={{
                flex: 1,
                textAlign: "center",
                padding: "8px 12px",
                borderRadius: 8,
                cursor: isAccessible ? "pointer" : "not-allowed",
                background: isActive ? C.accentDim + "40" : isPast ? C.cardAlt : "transparent",
                border: isActive ? `1px solid ${C.accent}` : isPast ? `1px solid ${C.border}` : "none",
                opacity: isAccessible ? 1 : 0.4,
                transition: "all 0.2s"
              }}
            >
              <div style={{ fontSize: 11, fontWeight: 700, color: isActive ? C.accent : isPast ? C.text : C.textMuted, marginBottom: 2 }}>
                {String(index + 1)}. {step.label}
              </div>
              <div style={{ fontSize: 9, color: C.textMuted }}>
                {step.sublabel}
              </div>
            </div>
            {index < STEPS.length - 1 && (
              <div style={{ width: 20, height: 1, background: index < currentIndex ? C.accent : C.border, margin: "0 4px" }} />
            )}
          </div>
        );
      })}
    </div>
  );
};

// Components
const Card = ({ children, style, glow }: { children: React.ReactNode; style?: React.CSSProperties; glow?: boolean }) => (
  <div style={{
    background: C.card, borderRadius: 12, padding: 20,
    border: `1px solid ${glow ? C.accent + "40" : C.border}`,
    boxShadow: glow ? `0 0 20px ${C.accent}15}` : "none",
    ...style
  }}>{children}</div>
);

const Badge = ({ text, color }: { text: string; color: string }) => (
  <span style={{
    display: "inline-block", padding: "3px 10px", borderRadius: 20,
    fontSize: 11, fontWeight: 700, background: color + "22", color,
    letterSpacing: 0.5, fontFamily: font,
  }}>{text}</span>
);

// NSE Segment Information
// Source: NSE Guide to Listing (https://www.nse.co.ke/wp-content/uploads/guide-to-listing-2.pdf)
const SEGMENTS: SegmentsType = {
  GEMS: {
    name: "GEMS (SMEs/Startups)",
    description: "Growth Enterprise Market Segment — designed for SMEs and startups",
    source: "NSE Guide to Listing, Part C",
    requirements: [
      { req: "KES 10M minimum issued share capital", icon: "💰" },
      { req: "100,000 minimum shares in issue", icon: "📜" },
      { req: "15% free float to public", icon: "📊" },
      { req: "2 years trading (1 year profit)", icon: "📅" }
    ]
  },
  AIMS: {
    name: "AIMS (Growing)",
    description: "Alternative Investment Market Segment — for growing companies",
    source: "NSE Guide to Listing, Part B",
    requirements: [
      { req: "KES 20M minimum issued share capital", icon: "💰" },
      { req: "KES 20M minimum net assets", icon: "💼" },
      { req: "20% to at least 100 shareholders", icon: "👥" },
      { req: "2 years existence (1 year profit)", icon: "📅" }
    ]
  },
  MIMS: {
    name: "MIMS (Main Market)",
    description: "Main Investment Market — for established blue-chip companies",
    source: "NSE Guide to Listing, Part A",
    requirements: [
      { req: "KES 50M minimum issued share capital", icon: "💰" },
      { req: "KES 100M minimum net assets", icon: "💼" },
      { req: "25% to at least 1,000 shareholders", icon: "👥" },
      { req: "Profits in 3 of last 5 years", icon: "📈" }
    ]
  }
};

const KEY_PARTIES = [
  { key: "lead_transaction_advisor", name: "Lead Transaction Advisor", essential: true, desc: "Coordinates entire IPO process" },
  { key: "sponsoring_broker", name: "Sponsoring Broker", essential: true, desc: "NSE-licensed broker" },
  { key: "legal_counsel", name: "Legal Counsel", essential: true, desc: "Legal aspects & documentation" },
  { key: "reporting_accountant", name: "Reporting Accountant", essential: true, desc: "Prepares financial info" },
  { key: "receiving_agent", name: "Receiving Agent", essential: false, desc: "Handles applications & payments" },
];

const REQUIRED_DOCUMENTS = [
  { key: "certificate_of_incorporation", name: "Certificate of Incorporation", essential: true },
  { key: "audited_financials_2yr", name: "2 Years Audited Financials", essential: true },
  { key: "draft_prospectus", name: "Draft Prospectus", essential: true },
  { key: "board_approval", name: "Board Resolution to List", essential: true },
  { key: "tax_compliance_certificate", name: "Tax Compliance Certificate", essential: true },
  { key: "crd_clearance", name: "CRD Clearance Certificate", essential: true },
  { key: "cma_pre_approval", name: "CMA Pre-approval", essential: false },
  { key: "shareholder_approval", name: "Shareholder Approval", essential: false },
];

// Initial form state
const initialFormData: FormData = {
  company_name: "",
  sector: "",
  segment: "GEMS",
  website: "",
  issued_share_capital: "",
  shareholders_count: "",
  free_float_percent: "",
  trading_years: "",
  revenue_years_count: "3", // "1", "2", or "3+"
  revenue_year_1: "", // Most recent year
  revenue_year_2: "", // Second year
  revenue_year_3: "", // Third year (if available)
  tax_compliant: true,
  litigation: "",
  board_members: [{ name: "", role: "", independent: false }],
  key_parties: [],
  documents_ready: []
};

// Generate dynamic years based on current date
const getRevenueYears = () => {
  const currentYear = new Date().getFullYear();
  return [
    { label: (currentYear - 1).toString(), key: "revenue_year_1" },  // e.g., 2025
    { label: (currentYear - 2).toString(), key: "revenue_year_2" }, // e.g., 2024
    { label: (currentYear - 3).toString(), key: "revenue_year_3" }  // e.g., 2023
  ];
};

export default function ListingScannerTab() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);
  const [formData, setFormData] = useState<FormData>(initialFormData);

  // NEW: State for document uploads and manual verification
  const [uploadedDocuments, setUploadedDocuments] = useState<Record<string, File>>({});
  const [manualVerification, setManualVerification] = useState({
    auditor_contact: "",
    kra_pin: "",
    crd_reference: ""
  });

  const handleSubmit = async () => {
    setLoading(true);
    setError(null);

    // Validate required fields
    if (!formData.company_name?.trim()) {
      setError("Company name is required");
      setLoading(false);
      return;
    }
    if (!formData.sector?.trim()) {
      setError("Sector is required");
      setLoading(false);
      return;
    }

    try {
      const payload = new FormData();
      payload.append("company_name", formData.company_name);
      payload.append("sector", formData.sector);
      payload.append("segment", formData.segment);
      if (formData.website) payload.append("website", formData.website);
      payload.append("issued_share_capital", String(parseInt(formData.issued_share_capital) || 0));
      payload.append("shareholders_count", String(parseInt(formData.shareholders_count) || 0));
      payload.append("free_float_percent", String(parseInt(formData.free_float_percent) || 0));
      payload.append("trading_years", String(parseFloat(formData.trading_years) || 0));

      // Build revenue history from dynamic years
      const revenueYears = getRevenueYears();
      const revenueHistory: Record<string, number> = {};
      const yearsCount = formData.revenue_years_count === "3+" ? 3 : (parseInt(formData.revenue_years_count) || 3);
      for (let i = 0; i < yearsCount; i++) {
        const yearInfo = revenueYears[i];
        const value = parseFloat(String(formData[yearInfo.key] || "0")) || 0;
        if (value > 0) {
          revenueHistory[yearInfo.label] = value;
        }
      }
      payload.append("revenue_history_json", JSON.stringify(revenueHistory));

      payload.append("board_members_json", JSON.stringify(
        (formData.board_members || []).filter(m => m?.name && m.name.trim())
      ));
      payload.append("tax_compliant", String(formData.tax_compliant));
      if (formData.litigation) payload.append("litigation", formData.litigation);
      payload.append("key_parties_json", JSON.stringify(formData.key_parties || []));
      payload.append("documents_ready_json", JSON.stringify(formData.documents_ready || []));

      // NEW: Append uploaded documents for verification
      if (uploadedDocuments.financials) {
        payload.append("financials_file", uploadedDocuments.financials);
      }
      if (uploadedDocuments.tax_cert) {
        payload.append("tax_cert_file", uploadedDocuments.tax_cert);
      }
      if (uploadedDocuments.board_resolution) {
        payload.append("board_resolution_file", uploadedDocuments.board_resolution);
      }
      if (uploadedDocuments.crd_cert) {
        payload.append("crd_cert_file", uploadedDocuments.crd_cert);
      }

      // NEW: Manual verification codes
      if (manualVerification.auditor_contact) {
        payload.append("auditor_contact", manualVerification.auditor_contact);
      }
      if (manualVerification.kra_pin) {
        payload.append("kra_pin", manualVerification.kra_pin);
      }
      if (manualVerification.crd_reference) {
        payload.append("crd_reference", manualVerification.crd_reference);
      }

      const response = await fetch(`${API_BASE}/listing/analyze-hybrid`, {
        method: "POST",
        body: payload,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
      setStep(5); // Go to results step
    } catch (err: unknown) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to analyze. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData(initialFormData);
    setResult(null);
    setError(null);
    setStep(1);
    setUploadedDocuments({});
    setManualVerification({ auditor_contact: "", kra_pin: "", crd_reference: "" });
  };

  const toggleKeyParty = (key: string) => {
    const current = formData.key_parties || [];
    if (current.includes(key)) {
      setFormData({ ...formData, key_parties: current.filter(k => k !== key) });
    } else {
      setFormData({ ...formData, key_parties: [...current, key] });
    }
  };

  const toggleDocument = (key: string) => {
    const current = formData.documents_ready || [];
    if (current.includes(key)) {
      setFormData({ ...formData, documents_ready: current.filter(k => k !== key) });
    } else {
      setFormData({ ...formData, documents_ready: [...current, key] });
    }
  };

  // NEW: Document upload handlers
  const handleDocumentUpload = (file: File, documentType: string) => {
    setUploadedDocuments(prev => ({ ...prev, [documentType]: file }));
  };

  const handleDocumentRemove = (documentType: string) => {
    setUploadedDocuments(prev => {
      const updated = { ...prev };
      delete updated[documentType];
      return updated;
    });
  };

  const handleManualVerificationChange = (
    field: "auditor_contact" | "kra_pin" | "crd_reference",
    value: string
  ) => {
    setManualVerification(prev => ({ ...prev, [field]: value }));
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return C.accent;
    if (score >= 60) return C.gold;
    return C.red;
  };

  // Step 1: Market Segment Selection
  if (step === 1) {
    return (
      <div>
        <StepNav currentStep={step} onStepClick={setStep} result={result} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 400px", gap: 20 }}>
        <Card>
          <h2 style={{ color: C.text, margin: "0 0 8px", fontSize: 20, fontWeight:700 }}>NSE Listing Readiness Scanner</h2>
          <p style={{ color: C.textMuted, margin: "0 0 30px", fontSize: 13, lineHeight: 1.6 }}>
            Get a comprehensive assessment of your company's readiness for NSE listing.
            We analyze both <strong>regulatory requirements</strong> and <strong>company health</strong>.
          </p>

          <div style={{ marginBottom: 20 }}>
            <label style={{ color: C.textDim, fontSize: 12, marginBottom: 12, display: "block", fontWeight: 500 }}>
              Which NSE segment are you targeting?
            </label>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {Object.entries(SEGMENTS).map(([key, segment]) => (
                <div
                  key={key}
                  onClick={() => setFormData({ ...formData, segment: key as "GEMS" | "AIMS" | "MIMS" })}
                  style={{
                    padding: 16, borderRadius: 12, background: formData.segment === key ? C.accentDim + "30" : C.cardAlt,
                    border: `1px solid ${formData.segment === key ? C.accent : C.border}`,
                    cursor: "pointer", transition: "all 0.2s"
                  }}
                >
                  <div style={{ fontSize: 14, fontWeight: 700, color: formData.segment === key ? C.accent : C.text, marginBottom: 4 }}>
                    {segment.name}
                  </div>
                  <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 8 }}>
                    {segment.description}
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                    {segment.requirements.slice(0, 4).map((req, i) => (
                      <span key={i} style={{ fontSize: 10, color: C.textDim }}>
                        {req.icon} {req.req}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <button
            onClick={() => setStep(2)}
            disabled={!formData.company_name}
            style={{
              marginTop: 10, padding: "12px 24px", background: C.accent, color: "#000",
              border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer",
              fontSize: 13, fontFamily: font
            }}
          >
            Wait, I need to enter company name first →
          </button>

          <input
            value={formData.company_name}
            onChange={e => setFormData({ ...formData, company_name: e.target.value })}
            placeholder="Enter your company name first..."
            style={{
              marginTop: 10, width: "100%", padding: "10px 14px", background: C.bg,
              border: `1px solid ${C.border}`, borderRadius: 8, color: C.text,
              fontSize: 13, outline: "none", fontFamily: font
            }}
          />
        </Card>

        <Card>
          <h3 style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 12 }}>About NSE Segments</h3>
          <div style={{ color: C.textDim, fontSize: 12, lineHeight: 1.8 }}>
            <p><strong>GEMS:</strong> For SMEs and startups. Lower barriers to entry.</p>
            <p><strong>AIMS:</strong> For growing companies scaling toward main market.</p>
            <p><strong>MIMS:</strong> For established blue-chip companies.</p>
            <div style={{ marginTop: 16, padding: 10, background: C.cardAlt, borderRadius: 8 }}>
              <div style={{ color: C.accent, fontSize: 11, fontWeight: 700, marginBottom: 4 }}>
                Why We Check Both
              </div>
              <div style={{ fontSize: 11, color: C.textMuted }}>
                Regulatory readiness = Can you legally list?<br/>
                Company health = Should you list?
              </div>
            </div>
          </div>
        </Card>
      </div>
      </div>
    );
  }

  // Step 2: Basic Info + NSE Requirements
  if (step === 2) {
    const segment = SEGMENTS[formData.segment];
    return (
      <div>
        <StepNav currentStep={step} onStepClick={setStep} result={result} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 400px", gap: 20 }}>
        <Card>
          <h2 style={{ color: C.text, margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>
            {segment?.name} Requirements
          </h2>
          <p style={{ color: C.textMuted, margin: "0 0 20px", fontSize: 12 }}>
            Enter your company details. We'll compare against {formData.segment} requirements.
          </p>

          {error && (
            <div style={{ padding: 12, background: C.red + "22", border: `1px solid ${C.red}`, borderRadius: 8, color: C.red, fontSize: 12, marginBottom: 16 }}>
              {error}
            </div>
          )}

          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {/* Company Name & Sector */}
            <div style={{ display: "flex", gap: 12 }}>
              <div style={{ flex: 1 }}>
                <label style={{ color: C.textDim, fontSize: 11, marginBottom: 4, fontWeight: 500 }}>Company Name *</label>
                <input
                  value={formData.company_name}
                  onChange={e => setFormData({ ...formData, company_name: e.target.value })}
                  placeholder="e.g., Copy Cat Limited"
                  style={{ width: "100%", padding: "10px 14px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 13 }}
                />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ color: C.textDim, fontSize: 11, marginBottom: 4, fontWeight: 500 }}>Sector *</label>
                <select
                  value={formData.sector}
                  onChange={e => setFormData({ ...formData, sector: e.target.value })}
                  style={{ width: "100%", padding: "10px 14px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 13 }}
                >
                  <option value="">Select sector...</option>
                  <option value="retail">Retail / FMCG</option>
                  <option value="technology">Technology</option>
                  <option value="fmcg">Fast-Moving Consumer Goods</option>
                  <option value="banking">Banking / Finance</option>
                  <option value="agriculture">Agriculture / Agritech</option>
                  <option value="manufacturing">Manufacturing</option>
                  <option value="energy">Energy / Renewable</option>
                  <option value="telecom">Telecommunications</option>
                  <option value="fintech">Fintech</option>
                  <option value="health">Health / Healthcare</option>
                  <option value="realestate">Real Estate / Construction</option>
                  <option value="transport">Transport / Logistics</option>
                </select>
              </div>
            </div>

            {/* Website */}
            <div>
              <label style={{ color: C.textDim, fontSize: 11, marginBottom: 4, fontWeight: 500 }}>Company Website</label>
              <input
                value={formData.website}
                onChange={e => setFormData({ ...formData, website: e.target.value })}
                placeholder="https://..."
                style={{ width: "100%", padding: "10px 14px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 13 }}
              />
            </div>

            {/* NSE Numeric Requirements */}
            <div style={{ padding: 12, background: C.cardAlt, borderRadius: 8 }}>
              <label style={{ color: C.accent, fontSize: 11, fontWeight: 700, marginBottom: 10, display: "block" }}>
                NSE {formData.segment} Numeric Requirements
              </label>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div>
                  <label style={{ color: C.textDim, fontSize: 10, marginBottom: 3 }}>Issued Share Capital (KES)</label>
                  <input
                    type="number"
                    value={formData.issued_share_capital}
                    onChange={e => setFormData({ ...formData, issued_share_capital: e.target.value })}
                    placeholder="e.g., 15000000"
                    style={{ width: "100%", padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 12 }}
                  />
                </div>
                <div>
                  <label style={{ color: C.textDim, fontSize: 10, marginBottom: 3 }}>Number of Shareholders</label>
                  <input
                    type="number"
                    value={formData.shareholders_count}
                    onChange={e => setFormData({ ...formData, shareholders_count: e.target.value })}
                    placeholder="e.g., 75"
                    style={{ width: "100%", padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 12 }}
                  />
                </div>
                <div>
                  <label style={{ color: C.textDim, fontSize: 10, marginBottom: 3 }}>Free Float (%)</label>
                  <input
                    type="number"
                    value={formData.free_float_percent}
                    onChange={e => setFormData({ ...formData, free_float_percent: e.target.value })}
                    placeholder="e.g., 20"
                    style={{ width: "100%", padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 12 }}
                  />
                </div>
                <div>
                  <label style={{ color: C.textDim, fontSize: 10, marginBottom: 3 }}>Trading History (years)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={formData.trading_years}
                    onChange={e => setFormData({ ...formData, trading_years: e.target.value })}
                    placeholder="e.g., 2.5"
                    style={{ width: "100%", padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 12 }}
                  />
                </div>
              </div>
            </div>

            {/* Revenue */}
            <div>
              <label style={{ color: C.textDim, fontSize: 11, marginBottom: 6, fontWeight: 500 }}>Revenue History (KES)</label>
              <div style={{ color: C.textMuted, fontSize: 10, marginBottom: 8 }}>
                How many years of revenue data do you have?
              </div>
              <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
                {["1", "2", "3+"].map((count) => (
                  <button
                    key={count}
                    type="button"
                    onClick={() => setFormData({ ...formData, revenue_years_count: count })}
                    style={{
                      flex: 1,
                      padding: "8px",
                      background: formData.revenue_years_count === count ? C.accentDim + "40" : C.cardAlt,
                      border: `1px solid ${formData.revenue_years_count === count ? C.accent : C.border}`,
                      borderRadius: 6,
                      color: formData.revenue_years_count === count ? C.accent : C.textDim,
                      fontSize: 11,
                      fontWeight: 600,
                      cursor: "pointer"
                    }}
                  >
                    {count === "3+" ? "3+ Years" : `${count} Year`}
                  </button>
                ))}
              </div>
              <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {getRevenueYears().slice(0, formData.revenue_years_count === "3+" ? 3 : parseInt(formData.revenue_years_count)).map((yearInfo, i) => (
                  <div key={i} style={{ flex: "1 1 120px" }}>
                    <input
                      value={String(formData[yearInfo.key] || "")}
                      onChange={e => setFormData({ ...formData, [yearInfo.key]: e.target.value })}
                      placeholder={`Year ${yearInfo.label}`}
                      style={{
                        width: "100%", padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 12
                      }}
                    />
                    <div style={{ color: C.textMuted, fontSize: 9, marginTop: 2 }}>{yearInfo.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Board Members */}
            <div>
              <label style={{ color: C.textDim, fontSize: 11, marginBottom: 6, fontWeight:500 }}>Board Members</label>
              {(formData.board_members || []).map((member, i) => (
                <div key={i} style={{ display: "flex", gap: 6, marginBottom: 6, alignItems: "center" }}>
                  <input
                    value={member.name || ""}
                    onChange={e => {
                      const board = formData.board_members || [];
                      const newBoard = [...board];
                      newBoard[i] = { ...newBoard[i], name: e.target.value };
                      setFormData({ ...formData, board_members: newBoard });
                    }}
                    placeholder="Full name"
                    style={{ flex: 2, padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 12 }}
                  />
                  <input
                    value={member.role || ""}
                    onChange={e => {
                      const board = formData.board_members || [];
                      const newBoard = [...board];
                      newBoard[i] = { ...newBoard[i], role: e.target.value };
                      setFormData({ ...formData, board_members: newBoard });
                    }}
                    placeholder="Role"
                    style={{ flex: 1, padding: "8px 12px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 12 }}
                  />
                  <label style={{ display: "flex", alignItems: "center", gap: 4, color: C.textDim, fontSize: 10 }}>
                    <input
                      type="checkbox"
                      checked={member.independent || false}
                      onChange={e => {
                        const board = formData.board_members || [];
                        const newBoard = [...board];
                        newBoard[i] = { ...newBoard[i], independent: e.target.checked };
                        setFormData({ ...formData, board_members: newBoard });
                      }}
                    />
                    Indep?
                  </label>
                  {(formData.board_members || []).length > 1 && (
                    <button
                      onClick={() => {
                        setFormData({
                          ...formData,
                          board_members: (formData.board_members || []).filter((_, idx) => idx !== i)
                        });
                      }}
                      style={{ padding: "2px 6px", background: C.red + "22", color: C.red, border: "none", borderRadius: 4, fontSize: 10 }}
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
              <button
                onClick={() => setFormData({
                  ...formData,
                  board_members: [...(formData.board_members || []), { name: "", role: "", independent: false }]
                })}
                style={{ fontSize: 11, color: C.blue, background: "none", border: "none", cursor: "pointer", padding: 0 }}
              >
                + Add Board Member
              </button>
            </div>

            {/* Compliance */}
            <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
              <label style={{ display: "flex", alignItems: "center", gap: 6, color: C.text, fontSize: 12 }}>
                <input
                  type="checkbox"
                  checked={formData.tax_compliant}
                  onChange={e => setFormData({ ...formData, tax_compliant: e.target.checked })}
                />
                Tax Compliant (KRA)
              </label>
            </div>

            <div>
              <label style={{ color: C.textDim, fontSize: 11, marginBottom: 4, fontWeight: 500 }}>Active Litigation (if any)</label>
              <input
                value={formData.litigation}
                onChange={e => setFormData({ ...formData, litigation: e.target.value })}
                placeholder="Describe any ongoing legal cases..."
                style={{ width: "100%", padding: "10px 14px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 12 }}
              />
            </div>

            {/* Navigation */}
            <div style={{ display: "flex", gap: 12, marginTop: 8 }}>
              <button
                onClick={() => setStep(1)}
                style={{ padding: "10px 20px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, color: C.textDim, cursor: "pointer", fontSize: 12 }}
              >
                ← Back
              </button>
              <button
                onClick={() => setStep(3)}
                style={{ flex: 1, padding: "10px 20px", background: C.accent, color: "#000", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer", fontSize: 12 }}
              >
                Continue →
              </button>
            </div>
          </div>
        </Card>

        <Card>
          <h3 style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 12 }}>
            {formData.segment} Requirements
          </h3>
          {segment?.requirements.map((req, i) => (
            <div key={i} style={{ fontSize: 11, color: C.textDim, padding: "4px 0", borderBottom: i < 4 ? `1px solid ${C.border}20` : "none" }}>
              {req.icon} {req.req}
            </div>
          ))}
        </Card>
      </div>
      </div>
    );
  }

  // Step 3a: Key Parties Appointed
  if (step === 3) {
    return (
      <div>
        <StepNav currentStep={step} onStepClick={setStep} result={result} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 400px", gap: 20 }}>
        <Card>
          <h2 style={{ color: C.text, margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>
            Key Parties Appointed
          </h2>
          <p style={{ color: C.textMuted, margin: "0 0 20px", fontSize: 12 }}>
            NSE requires specific parties for listing. Which have you appointed?
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {KEY_PARTIES.map((party, i) => (
              <div
                key={i}
                onClick={() => toggleKeyParty(party.key)}
                style={{
                  padding: 12, background: C.cardAlt, borderRadius: 8, cursor: "pointer",
                  border: `1px solid ${formData.key_parties?.includes(party.key) ? C.accent : C.border}`,
                  display: "flex", alignItems: "center", gap: 10
                }}
              >
                <div style={{
                  width: 20, height: 20, borderRadius: formData.key_parties?.includes(party.key) ? C.accent : C.border,
                  background: formData.key_parties?.includes(party.key) ? C.accentDim : "transparent",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: formData.key_parties?.includes(party.key) ? "#000" : C.textMuted, fontSize: 12
                }}>
                  {formData.key_parties?.includes(party.key) ? "✓" : "○"}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: C.text }}>{party.name}</div>
                  <div style={{ fontSize: 10, color: C.textMuted }}>{party.desc}</div>
                </div>
                {party.essential && (
                  <Badge text="Required" color={C.red} />
                )}
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
            <button
              onClick={() => setStep(2)}
              style={{ padding: "10px 20px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, color: C.textDim, cursor: "pointer", fontSize: 12 }}
            >
              ← Back
            </button>
            <button
              onClick={() => setStep(3.1)}
              style={{ flex: 1, padding: "10px 20px", background: C.accent, color: "#000", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer", fontSize: 12 }}
            >
              Next: Documents →
            </button>
          </div>
        </Card>

        <Card>
          <h3 style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 12 }}>
            Why Key Parties Matter
          </h3>
          <div style={{ color: C.textDim, fontSize: 12, lineHeight: 1.8 }}>
            <p>NSE listing is a team sport. You need professionals who understand the process:</p>
            <ul style={{ margin: "12px 0", paddingLeft: 20 }}>
              <li><strong>Lead Transaction Advisor:</strong> Your project manager for the IPO</li>
              <li><strong>Sponsoring Broker:</strong> Required by NSE to handle share applications</li>
              <li><strong>Legal Counsel:</strong> Ensures all documentation meets CMA/NSE standards</li>
            </ul>
            <div style={{ marginTop: 16, padding: 10, background: C.cardAlt, borderRadius: 8 }}>
              <div style={{ color: C.gold, fontSize: 11, fontWeight: 700, marginBottom: 4 }}>
                💡 Pro Tip
              </div>
              <div style={{ fontSize: 11, color: C.textMuted }}>
                Start with a Lead Transaction Advisor — they can help identify and appoint the other required parties.
              </div>
            </div>
          </div>
        </Card>
      </div>
      </div>
    );
  }

  // Step 3b: Document Readiness
  if (step === 3.1) {
    return (
      <div>
        <StepNav currentStep={step} onStepClick={setStep} result={result} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 400px", gap: 20 }}>
        <Card>
          <h2 style={{ color: C.text, margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>
            Document Readiness
          </h2>
          <p style={{ color: C.textMuted, margin: "0 0 20px", fontSize: 12 }}>
            Which documents do you currently have ready?
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {REQUIRED_DOCUMENTS.map((doc, i) => (
              <div
                key={i}
                onClick={() => toggleDocument(doc.key)}
                style={{
                  padding: 10, background: C.cardAlt, borderRadius: 6, cursor: "pointer",
                  border: `1px solid ${formData.documents_ready?.includes(doc.key) ? C.accent : C.border}`,
                  display: "flex", alignItems: "center", gap: 10
                }}
              >
                <div style={{
                  width: 18, height: 18, borderRadius: formData.documents_ready?.includes(doc.key) ? C.accent : C.border,
                  background: formData.documents_ready?.includes(doc.key) ? C.accentDim : "transparent",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  color: formData.documents_ready?.includes(doc.key) ? "#000" : C.textMuted, fontSize: 11
                }}>
                  {formData.documents_ready?.includes(doc.key) ? "✓" : "○"}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, color: C.text }}>{doc.name}</div>
                </div>
                {doc.essential && <Badge text="Required" color={C.red} />}
              </div>
            ))}
          </div>

          <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
            <button
              onClick={() => setStep(3)}
              style={{ padding: "10px 20px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, color: C.textDim, cursor: "pointer", fontSize: 12 }}
            >
              ← Back
            </button>
            <button
              onClick={() => setStep(3.2)}
              style={{ flex: 1, padding: "10px 20px", background: C.accent, color: "#000", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer", fontSize: 12 }}
            >
              Next: Verification Uploads →
            </button>
          </div>
        </Card>

        <Card>
          <h3 style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 12 }}>
            Document Timeline
          </h3>
          <div style={{ color: C.textDim, fontSize: 12, lineHeight: 1.8 }}>
            <p>Don't have all documents yet? That's okay — most can be prepared in parallel with your listing application.</p>
            <div style={{ marginTop: 12 }}>
              <div style={{ color: C.text, fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Can be prepared now:</div>
              <div style={{ fontSize: 10, color: C.textMuted, marginLeft: 8 }}>
                ✓ Certificate of Incorporation<br/>
                ✓ Board Resolution to List<br/>
                ✓ 2 Years Audited Financials
              </div>
            </div>
            <div style={{ marginTop: 12 }}>
              <div style={{ color: C.text, fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Requires application process:</div>
              <div style={{ fontSize: 10, color: C.textMuted, marginLeft: 8 }}>
                ✓ Tax Compliance Certificate (KRA)<br/>
                ✓ CRD Clearance Certificate<br/>
                ✓ CMA Pre-approval
              </div>
            </div>
            <div style={{ marginTop: 16, padding: 10, background: C.cardAlt, borderRadius: 8 }}>
              <div style={{ color: C.accent, fontSize: 11, fontWeight: 700, marginBottom: 4 }}>
                📄 Next Step
              </div>
              <div style={{ fontSize: 11, color: C.textMuted }}>
                After checking what you have, you can upload documents for <strong>real verification</strong> on the next page.
              </div>
            </div>
          </div>
        </Card>
      </div>
      </div>
    );
  }

  // Step 3c: Verification Uploads (only shows documents checked as ready)
  if (step === 3.2) {
    // Map document keys to upload configuration
    const uploadableDocs: Record<string, { label: string; description: string; documentType: string }> = {
      "audited_financials_2yr": {
        label: "Audited Financial Statements",
        description: "Required for revenue verification. Upload 2 years of audited financials.",
        documentType: "financials"
      },
      "tax_compliance_certificate": {
        label: "Tax Compliance Certificate",
        description: "Required for compliance verification. KRA-issued certificate.",
        documentType: "tax_cert"
      },
      "board_approval": {
        label: "Board Resolution to List",
        description: "Required for governance verification. Signed by the board.",
        documentType: "board_resolution"
      },
      "crd_clearance": {
        label: "CRD Clearance Certificate",
        description: "Required for regulatory verification from CMA.",
        documentType: "crd_cert"
      }
    };

    // Get the documents that were checked as ready
    const readyForUpload = (formData.documents_ready || [])
      .filter(key => uploadableDocs[key])
      .map(key => ({ key, ...uploadableDocs[key] }));

    return (
      <div>
        <StepNav currentStep={step} onStepClick={setStep} result={result} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 400px", gap: 20 }}>
        <Card>
          <h2 style={{ color: C.text, margin: "0 0 8px", fontSize: 18, fontWeight: 700 }}>
            Verification Uploads
          </h2>
          <p style={{ color: C.textMuted, margin: "0 0 20px", fontSize: 12 }}>
            Upload documents for <strong style={{ color: C.accent }}>real verification</strong>. Only documents you marked as "ready" are shown below.
          </p>

          {readyForUpload.length === 0 ? (
            <div style={{ padding: 20, background: C.cardAlt, borderRadius: 8, textAlign: "center" }}>
              <div style={{ fontSize: 20, marginBottom: 8 }}>📋</div>
              <div style={{ fontSize: 12, color: C.textDim }}>
                No documents marked as ready. Go back to check off documents you have.
              </div>
            </div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {readyForUpload.map(doc => (
                <DocumentUpload
                  key={doc.key}
                  documentType={doc.documentType}
                  label={doc.label}
                  description={doc.description}
                  accept=".pdf,image/*"
                  onUpload={handleDocumentUpload}
                  onRemove={handleDocumentRemove}
                  uploadedFile={uploadedDocuments[doc.documentType]}
                />
              ))}
            </div>
          )}

          {/* Manual Verification Entry - always shown */}
          <div style={{ marginTop: 20, padding: 16, background: C.cardAlt, borderRadius: 8, border: `1px solid ${C.border}` }}>
            <div style={{ fontSize: 11, color: C.textDim, marginBottom: 12 }}>
              <strong>Alternative:</strong> Enter verification codes manually (format validation only):
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8 }}>
              <div>
                <div style={{ fontSize: 10, fontWeight: 500, color: C.textDim, marginBottom: 4 }}>Auditor Email/Phone</div>
                <input
                  type="text"
                  placeholder="auditor@firm.com"
                  value={manualVerification.auditor_contact}
                  onChange={(e) => handleManualVerificationChange("auditor_contact", e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 11, outline: "none" }}
                />
              </div>
              <div>
                <div style={{ fontSize: 10, fontWeight: 500, color: C.textDim, marginBottom: 4 }}>KRA Tax PIN</div>
                <input
                  type="text"
                  placeholder="A00xxxxxxxx"
                  value={manualVerification.kra_pin}
                  onChange={(e) => handleManualVerificationChange("kra_pin", e.target.value)}
                  maxLength={11}
                  style={{ width: "100%", padding: "8px 10px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 11, outline: "none" }}
                />
              </div>
              <div>
                <div style={{ fontSize: 10, fontWeight: 500, color: C.textDim, marginBottom: 4 }}>CRD Reference #</div>
                <input
                  type="text"
                  placeholder="CRD-XXXXXX"
                  value={manualVerification.crd_reference}
                  onChange={(e) => handleManualVerificationChange("crd_reference", e.target.value)}
                  style={{ width: "100%", padding: "8px 10px", background: C.bg, border: `1px solid ${C.border}`, borderRadius: 6, color: C.text, fontSize: 11, outline: "none" }}
                />
              </div>
            </div>
          </div>

          <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
            <button
              onClick={() => setStep(3.1)}
              style={{ padding: "10px 20px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, color: C.textDim, cursor: "pointer", fontSize: 12 }}
            >
              ← Back
            </button>
            <button
              onClick={() => setStep(4)}
              style={{ flex: 1, padding: "10px 20px", background: C.accent, color: "#000", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer", fontSize: 12 }}
            >
              Review & Submit →
            </button>
          </div>
        </Card>

        <Card>
          <h3 style={{ color: C.text, fontSize: 14, fontWeight: 700, marginBottom: 12 }}>
            Why Upload Documents?
          </h3>
          <div style={{ color: C.textDim, fontSize: 12, lineHeight: 1.8 }}>
            <p><strong style={{ color: C.accent }}>Real verification beats "public cross-check"</strong></p>
            <p style={{ fontSize: 11 }}>Most SMEs have no public data available. News scraping only works for large, well-known companies. By uploading your documents, we can:</p>
            <ul style={{ margin: "12px 0", paddingLeft: 20, fontSize: 11 }}>
              <li>Verify revenue figures from your audited financials</li>
              <li>Confirm tax compliance status</li>
              <li>Validate board governance via resolution</li>
              <li>Check regulatory clearance (CRD)</li>
            </ul>
            <div style={{ marginTop: 16, padding: 10, background: C.cardAlt, borderRadius: 8 }}>
              <div style={{ color: C.accent, fontSize: 11, fontWeight: 700, marginBottom: 4 }}>
                🔒 Your Data
              </div>
              <div style={{ fontSize: 11, color: C.textMuted }}>
                Documents are analyzed by AI and <strong>not stored permanently</strong>. Verification is session-based.
              </div>
            </div>
            <div style={{ marginTop: 12, padding: 10, background: C.cardAlt, borderRadius: 8 }}>
              <div style={{ color: C.gold, fontSize: 11, fontWeight: 700, marginBottom: 4 }}>
                📎 Upload Tips
              </div>
              <div style={{ fontSize: 11, color: C.textMuted }}>
                • PDF or image files (max 10MB each)<br/>
                • Clear, readable scans preferred<br/>
                • Manual codes = format check only
              </div>
            </div>
          </div>
        </Card>
      </div>
      </div>
    );
  }

  // Step 4: Review & Submit
  if (step === 4) {
    const segment = SEGMENTS[formData.segment];
    const partiesAppointed = formData.key_parties?.length || 0;
    const documentsReady = formData.documents_ready?.length || 0;
    const essentialParties = KEY_PARTIES.filter(p => p.essential).length;
    const essentialDocs = REQUIRED_DOCUMENTS.filter(d => d.essential).length;

    return (
      <div>
        <StepNav currentStep={step} onStepClick={setStep} result={result} />
        <Card style={{ maxWidth: 700, margin: "0 auto" }}>
        <h2 style={{ color: C.text, margin: "0 0 8px", fontSize: 18, fontWeight:700 }}>
          Review & Submit
        </h2>
        <p style={{ color: C.textMuted, margin: "0 0 20px", fontSize: 12 }}>
          Review your information before submitting for analysis.
        </p>

        {/* Summary */}
        <div style={{ background: C.cardAlt, padding: 16, borderRadius: 8, marginBottom: 20 }}>
          <div style={{ fontSize: 12, color: C.text, marginBottom: 12, fontWeight: 700 }}>
            Company: {formData.company_name || "Not specified"}
          </div>
          <div style={{ fontSize: 12, color: C.textDim, marginBottom: 4 }}>
            Segment: {segment?.name}
          </div>
          <div style={{ fontSize: 12, color: C.textDim, marginBottom: 4 }}>
            Sector: {formData.sector || "Not specified"}
          </div>
          <div style={{ fontSize: 12, color: C.textDim }}>
            Key Parties: {partiesAppointed}/{essentialParties} appointed
          </div>
          <div style={{ fontSize: 12, color: C.textDim }}>
            Documents: {documentsReady}/{essentialDocs} ready
          </div>
        </div>

        {error && (
          <div style={{ padding: 12, background: C.red + "22", border: `1px solid ${C.red}`, borderRadius: 8, color: C.red, fontSize: 12, marginBottom: 16 }}>
            {error}
          </div>
        )}

        {/* Navigation */}
        <div style={{ display: "flex", gap: 12 }}>
          <button
            onClick={() => setStep(3.2)}
            style={{ padding: "10px 20px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, color: C.textDim, cursor: "pointer", fontSize: 12 }}
          >
            ← Back
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading || !formData.company_name || !formData.sector}
            style={{ flex: 1, padding: "12px 24px", background: C.accent, color: "#000", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer", fontSize: 13 }}
          >
            {loading ? "Analyzing..." : "Analyze Readiness →"}
          </button>
        </div>
      </Card>
      </div>
    );
  }

  // Step 5: Enhanced Results
  if (step === 5 && result) {
    const companyHealth = result.company_health;
    const regulatory = result.regulatory_readiness;

    const radarData = [
      { dimension: "Revenue", score: companyHealth.dimensions.revenue.score, fullMark: 10 },
      { dimension: "Governance", score: companyHealth.dimensions.governance.score, fullMark: 10 },
      { dimension: "Growth", score: companyHealth.dimensions.growth.score, fullMark: 10 },
      { dimension: "Compliance", score: companyHealth.dimensions.compliance.score, fullMark: 10 },
      { dimension: "Market", score: companyHealth.dimensions.market_size.score, fullMark: 10 },
      { dimension: "Timing", score: companyHealth.dimensions.timing.score, fullMark: 10 },
    ];

    const companyHealthColor = getScoreColor(companyHealth.overall_score);
    const regulatoryColor = getScoreColor(regulatory.overall_score);

    return (
      <div>
        <StepNav currentStep={step} onStepClick={(s) => setStep(s === 6 ? 5 : s)} result={result} />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        {/* Left: Company Health */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div>
                <h3 style={{ color: C.text, fontSize: 14, fontWeight: 700, margin: 0 }}>Company Health</h3>
                <div style={{ color: C.textMuted, fontSize: 10, marginTop: 2 }}>
                  Should you list? Will investors buy?
                </div>
              </div>
              <Badge text={companyHealth.recommendation} color={companyHealthColor} />
            </div>

            <div style={{ textAlign: "center", marginBottom: 16 }}>
              <div style={{ fontSize: 48, fontWeight: 900, color: companyHealthColor, lineHeight: 1 }}>
                {companyHealth.overall_score}
              </div>
              <div style={{ color: C.textMuted, fontSize: 10, textTransform: "uppercase", letterSpacing: 1 }}>
                Company Health Score
              </div>
            </div>

            <ResponsiveContainer width="100%" height={200}>
              <RadarChart data={radarData}>
                <PolarGrid stroke={C.border} />
                <PolarAngleAxis dataKey="dimension" tick={{ fill: C.textDim, fontSize: 10 }} />
                <PolarRadiusAxis angle={90} domain={[0, 10]} tick={{ fill: C.textMuted, fontSize: 9 }} tickCount={5} />
                <Radar name="Score" dataKey="score" stroke={C.accent} fill={C.accent} fillOpacity={0.3} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>

            {/* Dimension Breakdowns */}
            <div style={{ marginTop: 8 }}>
              <div style={{ fontSize: 10, color: C.textMuted, marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>
                Score Breakdown
              </div>
              {Object.entries(companyHealth.dimensions).map(([key, dim]: [string, any]) => {
                const scoreColor = dim.score >= 7 ? C.accent : dim.score >= 4 ? C.gold : C.red;
                return (
                  <div key={key} style={{
                    padding: "8px 10px",
                    background: C.cardAlt,
                    borderRadius: 6,
                    marginBottom: 6,
                    borderLeft: `3px solid ${scoreColor}`
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: C.text }}>
                        {key === "market_size" ? "Market Size" : key.charAt(0).toUpperCase() + key.slice(1)}
                      </span>
                      <span style={{ fontSize: 11, fontWeight: 700, color: scoreColor }}>
                        {dim.score}/10
                      </span>
                    </div>
                    <div style={{ fontSize: 10, color: C.textDim, lineHeight: 1.4 }}>
                      {dim.breakdown?.reasoning || "Based on company input analysis"}
                    </div>
                    <div style={{ fontSize: 9, color: C.textMuted, marginTop: 4, display: "flex", alignItems: "center", gap: 4 }}>
                      <span>📊</span>
                      <span>{dim.breakdown?.data_source || "Company input"}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Combined Recommendation */}
          <Card style={{ background: C.cardAlt, borderColor: C.accent + "30" }}>
            <div style={{ fontSize: 11, color: C.accent, fontWeight: 700, marginBottom: 8, textTransform: "uppercase" }}>
              Combined Analysis
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.6, color: C.text }}>
              {result.combined_recommendation}
            </div>
          </Card>

          {/* Data Sources */}
          <Card style={{ background: C.cardAlt }}>
            <div style={{ fontSize: 11, color: C.blue, fontWeight: 700, marginBottom: 8 }}>
              📚 Data Sources
            </div>
            <div style={{ fontSize: 10, color: C.textDim, display: "flex", flexDirection: "column", gap: 4 }}>
              <div>✓ <strong>Company Input</strong> — Your provided financials, board, and documents</div>
              <div>✓ <strong>NSE Rules</strong> — Segment requirements (GEMS/AIMS/MIMS)</div>
              <div>✓ <strong>Public Cross-Check</strong> — News scraping (limited to companies mentioned in Business Daily/The Star)</div>
              <div>✓ <strong>Document Upload</strong> — For real verification via uploaded documents (recommended)</div>
            </div>
            <div style={{ fontSize: 9, color: C.warning, marginTop: 8, fontStyle: "italic" }}>
              ⚠️ Public data for most SMEs is limited. Upload documents for real verification.
            </div>
          </Card>
        </div>

        {/* Right: Regulatory Readiness */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <div>
                <h3 style={{ color: C.text, fontSize: 14, fontWeight: 700, margin: 0 }}>Regulatory Readiness</h3>
                <div style={{ color: C.textMuted, fontSize: 10, marginTop:2 }}>
                  Can you legally list on {result.segment}?
                </div>
              </div>
              <Badge text={`${regulatory.overall_score}%`} color={regulatoryColor} />
            </div>

            {/* Timeline */}
            <div style={{ padding: 12, background: C.cardAlt, borderRadius: 8, marginBottom: 12, display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ fontSize: 24, fontWeight: 700, color: C.accent }}>⏱</div>
              <div>
                <div style={{ fontSize: 11, color: C.textMuted }}>Estimated Time to Listing</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: C.text }}>{regulatory.timeline_estimate}</div>
              </div>
            </div>

            {/* Requirements Status */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: C.textDim, marginBottom: 6 }}>NSE Requirements ({regulatory.requirements.met}/{regulatory.requirements.total} met)</div>
              {regulatory.requirements.results.map((req: any, i: number) => (
                <div key={i} style={{ fontSize: 11, padding: "4px 0", color: req.status === "met" ? C.accent : req.status === "waiver_possible" ? C.gold : C.red }}>
                  {req.display}
                </div>
              ))}
            </div>

            {/* Key Parties */}
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: C.textDim, marginBottom: 6 }}>Key Parties ({regulatory.key_parties.appointed}/{regulatory.key_parties.total})</div>
              {regulatory.key_parties.details.map((party: any, i: number) => (
                <div key={i} style={{ fontSize: 11, padding: "3px 0", color: party.appointed ? C.accent : C.textMuted }}>
                  {party.appointed ? "✓" : "○"} {party.name}
                </div>
              ))}
            </div>

            {/* Documents */}
            <div>
              <div style={{ fontSize: 11, color: C.textDim, marginBottom: 6 }}>Documents ({regulatory.documents.ready}/{regulatory.documents.total})</div>
              {regulatory.documents.missing.length > 0 && (
                <div style={{ fontSize: 10, color: C.gold, marginBottom: 4 }}>
                  Missing: {regulatory.documents.missing.slice(0, 3).join(", ")}{regulatory.documents.missing.length > 3 && "..."}
                </div>
              )}
            </div>
          </Card>

          {/* Quick Wins */}
          {regulatory.quick_wins && regulatory.quick_wins.length > 0 && (
            <Card>
              <div style={{ fontSize: 11, color: C.accent, fontWeight: 700, marginBottom: 8 }}>Quick Wins</div>
              {regulatory.quick_wins.map((win: string, i: number) => (
                <div key={i} style={{ fontSize: 11, color: C.textDim, padding: "4px 0", borderBottom: i < regulatory.quick_wins.length - 1 ? `1px solid ${C.border}20` : "none" }}>
                  • {win}
                </div>
              ))}
            </Card>
          )}

          {/* Verification Report */}
          {result.verification && (result.verification.confirmations?.length > 0 || result.verification.discrepancies?.length > 0 || result.verification.red_flags?.length > 0) && (
            <Card>
              <div style={{ fontSize: 11, color: C.blue, fontWeight: 700, marginBottom: 8 }}>News Cross-Check (Limited)</div>
              {result.verification.confirmations?.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ color: C.accent, fontSize: 10, fontWeight: 700, marginBottom: 4 }}>✓ Verified ({result.verification.confirmations.length})</div>
                  {result.verification.confirmations.slice(0, 2).map((c: any, i: number) => (
                    <div key={i} style={{ fontSize: 10, color: C.textDim }}>{c.field}: {c.value}</div>
                  ))}
                </div>
              )}
              {result.verification.discrepancies?.length > 0 && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ color: C.gold, fontSize: 10, fontWeight: 700, marginBottom: 4 }}>⚠ Discrepancies ({result.verification.discrepancies.length})</div>
                  {result.verification.discrepancies.map((d: any, i: number) => (
                    <div key={i} style={{ fontSize: 10, color: C.textDim }}>↪ {d.field}: {d.claimed} vs public: {d.public}</div>
                  ))}
                </div>
              )}
              <div style={{ fontSize: 9, color: C.textMuted, marginTop: 8, fontStyle: "italic" }}>
                Note: Only checks news articles. Most SMEs have no public data to cross-reference.
              </div>
            </Card>
          )}

          {/* Reset Button */}
          <button
            onClick={resetForm}
            style={{ padding: "12px 24px", background: C.blue, color: "#fff", border: "none", borderRadius: 6, fontWeight: 700, cursor: "pointer", fontSize: 13 }}
          >
            Scan Another Company
          </button>
          <button
            onClick={() => setStep(4)}
            style={{ padding: "12px 24px", background: "transparent", border: `1px solid ${C.border}`, borderRadius: 6, fontWeight: 700, cursor: "pointer", fontSize: 13, color: C.textDim, marginLeft: 12 }}
          >
            ← Edit & Resubmit
          </button>
        </div>
      </div>
      </div>
    );
  }

  return null;
}
