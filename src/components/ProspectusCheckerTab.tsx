import { useState, useRef } from "react";

const C = {
  bg: "#060B18", card: "#0D1425", cardAlt: "#111D33", border: "#1A2744",
  accent: "#10B981", accentDim: "#065F46", blue: "#3B82F6",
  gold: "#F59E0B", red: "#EF4444", purple: "#8B5CF6",
  text: "#F1F5F9", textDim: "#94A3B8", textMuted: "#64748B",
};

const font = "'Segoe UI', system-ui, sans-serif";

interface Gap {
  section: string;
  issue: string;
  severity: "critical" | "major" | "minor";
  recommendation: string;
}

interface ComplianceResult {
  filename: string;
  compliance_score: number;
  sections_reviewed: string[];
  gaps: Gap[];
  missing_sections: string[];
  overall_recommendation: string;
  cma_reference: string;
  disclaimer: string;
  analyzed_at: string;
}

const Card = ({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) => (
  <div style={{
    background: C.card, borderRadius: 12, padding: 20,
    border: `1px solid ${C.border}`, ...style
  }}>{children}</div>
);

const Badge = ({ text, color }: { text: string; color: string }) => (
  <span style={{
    display: "inline-block", padding: "3px 10px", borderRadius: 20,
    fontSize: 11, fontWeight: 700, background: color + "22", color,
    letterSpacing: 0.5, fontFamily: font,
  }}>{text}</span>
);

export default function ProspectusCheckerTab() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ComplianceResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (selectedFile: File) => {
    setError(null);
    setResult(null);

    // Validate file type
    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setError("Only PDF files are accepted. Please upload a .pdf file.");
      return;
    }

    // Validate file size (10MB max)
    const maxSize = 10 * 1024 * 1024;
    if (selectedFile.size > maxSize) {
      setError("File too large. Maximum size is 10MB.");
      return;
    }

    setFile(selectedFile);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch("http://localhost:8000/api/v1/prospectus/check", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || "Upload failed");
      }

      const data = await response.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Failed to analyze prospectus. Please ensure the backend is running.");
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical": return C.red;
      case "major": return C.gold;
      case "minor": return C.blue;
      default: return C.textDim;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 70) return C.accent;
    if (score >= 50) return C.gold;
    return C.red;
  };

  const getRecommendationBadge = (score: number) => {
    if (score >= 90) return { text: "Ready for CMA", color: C.accent };
    if (score >= 70) return { text: "Minor Revisions", color: C.gold };
    if (score >= 50) return { text: "Major Gaps", color: C.gold };
    return { text: "Significant Work", color: C.red };
  };

  // Results View
  if (result) {
    const scoreColor = getScoreColor(result.compliance_score);
    const badge = getRecommendationBadge(result.compliance_score);
    const criticalGaps = result.gaps.filter(g => g.severity === "critical");
    const majorGaps = result.gaps.filter(g => g.severity === "major");
    const minorGaps = result.gaps.filter(g => g.severity === "minor");

    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1.2fr", gap: 20 }}>
        {/* Left: Score and Overview */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <Card>
            <div style={{ textAlign: "center", marginBottom: 24 }}>
              <div style={{ fontSize: 13, color: C.textMuted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>
                CMA Compliance Score
              </div>
              <div style={{
                fontSize: 96, fontWeight: 900, color: scoreColor,
                lineHeight: 1, marginBottom: 8
              }}>
                {result.compliance_score}
              </div>
              <Badge text={badge.text} color={badge.color} />
            </div>

            <div style={{ paddingTop: 16, borderTop: `1px solid ${C.border}` }}>
              <div style={{ fontSize: 12, color: C.textMuted, marginBottom: 8 }}>
                Overall Recommendation
              </div>
              <div style={{ fontSize: 14, lineHeight: 1.6, color: C.text }}>
                {result.overall_recommendation}
              </div>
            </div>

            <div style={{ paddingTop: 16, borderTop: `1px solid ${C.border}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ fontSize: 11, color: C.textMuted }}>
                  Analyzed: {new Date(result.analyzed_at).toLocaleString()}
                </div>
                <Badge text={result.sections_reviewed.length + " Sections"} color={C.blue} />
              </div>
            </div>
          </Card>

          {/* Sections Reviewed */}
          <Card>
            <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: C.text }}>
              Sections Reviewed
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {result.sections_reviewed.map((section, i) => (
                <span key={i} style={{
                  padding: "4px 10px", background: C.cardAlt,
                  border: `1px solid ${C.border}`,
                  borderRadius: 6, fontSize: 11, color: C.textDim
                }}>
                  {section}
                </span>
              ))}
            </div>
          </Card>

          {/* CMA Reference */}
          <Card style={{ background: C.cardAlt }}>
            <div style={{ fontSize: 11, color: C.accent, marginBottom: 6 }}>
              CMA KENYA REFERENCE
            </div>
            <a
              href={result.cma_reference}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 12, color: C.blue, textDecoration: "none" }}
            >
              {result.cma_reference} →
            </a>
            <div style={{ fontSize: 10, color: C.textMuted, marginTop: 8, fontStyle: "italic" }}>
              {result.disclaimer}
            </div>
          </Card>

          <button
            onClick={() => { setFile(null); setResult(null); setError(null); }}
            style={{
              padding: "12px 24px", background: C.blue, color: "#fff",
              border: "none", borderRadius: 8, fontWeight: 700, cursor: "pointer",
              fontSize: 13, fontFamily: font, width: "100%"
            }}
          >
            Check Another Prospectus
          </button>
        </div>

        {/* Right: Detailed Gaps */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Missing Sections */}
          {result.missing_sections.length > 0 && (
            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: C.red }}>
                ⚠ Missing Sections ({result.missing_sections.length})
              </div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {result.missing_sections.map((section, i) => (
                  <li key={i} style={{ fontSize: 12, color: C.textDim, marginBottom: 4 }}>
                    {section}
                  </li>
                ))}
              </ul>
            </Card>
          )}

          {/* Critical Gaps */}
          {criticalGaps.length > 0 && (
            <Card style={{ borderColor: C.red + "40" }}>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: C.red }}>
                🔴 Critical Gaps ({criticalGaps.length})
              </div>
              {criticalGaps.map((gap, i) => (
                <div key={i} style={{
                  padding: 12, background: C.red + "10",
                  borderRadius: 8, marginBottom: i < criticalGaps.length - 1 ? 8 : 0
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 4 }}>
                    {gap.section}
                  </div>
                  <div style={{ fontSize: 11, color: C.textDim, marginBottom: 6 }}>
                    {gap.issue}
                  </div>
                  <div style={{ fontSize: 11, color: C.accent }}>
                    <strong>Fix:</strong> {gap.recommendation}
                  </div>
                </div>
              ))}
            </Card>
          )}

          {/* Major Gaps */}
          {majorGaps.length > 0 && (
            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: C.gold }}>
                ⚠ Major Gaps ({majorGaps.length})
              </div>
              {majorGaps.map((gap, i) => (
                <div key={i} style={{
                  padding: 12, background: C.cardAlt,
                  borderRadius: 8, marginBottom: i < majorGaps.length - 1 ? 8 : 0
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 4 }}>
                    {gap.section}
                  </div>
                  <div style={{ fontSize: 11, color: C.textDim, marginBottom: 6 }}>
                    {gap.issue}
                  </div>
                  <div style={{ fontSize: 11, color: C.accent }}>
                    <strong>Fix:</strong> {gap.recommendation}
                  </div>
                </div>
              ))}
            </Card>
          )}

          {/* Minor Gaps */}
          {minorGaps.length > 0 && (
            <Card>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: C.blue }}>
                ℹ Minor Gaps ({minorGaps.length})
              </div>
              {minorGaps.map((gap, i) => (
                <div key={i} style={{
                  padding: 10, background: C.cardAlt,
                  borderRadius: 8, marginBottom: i < minorGaps.length - 1 ? 8 : 0
                }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: C.text, marginBottom: 2 }}>
                    {gap.section}
                  </div>
                  <div style={{ fontSize: 11, color: C.textDim }}>
                    {gap.recommendation}
                  </div>
                </div>
              ))}
            </Card>
          )}

          {/* No Gaps Message */}
          {result.gaps.length === 0 && result.missing_sections.length === 0 && (
            <Card glow style={{ borderColor: C.accent + "40" }}>
              <div style={{ textAlign: "center", padding: 20 }}>
                <div style={{ fontSize: 48, marginBottom: 12 }}>✅</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: C.accent, marginBottom: 8 }}>
                  Excellent Work!
                </div>
                <div style={{ fontSize: 13, color: C.textDim }}>
                  Your prospectus meets all the CMA requirements we checked. Ready for submission.
                </div>
              </div>
            </Card>
          )}
        </div>
      </div>
    );
  }

  // Upload View
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 400px", gap: 20 }}>
      <Card>
        <h2 style={{ color: C.text, marginBottom: 8 }}>Prospectus Compliance Checker</h2>
        <p style={{ color: C.textMuted, fontSize: 13, marginBottom: 24, lineHeight: 1.6 }}>
          Upload your draft prospectus PDF for AI-powered CMA Kenya compliance analysis.
          Get instant feedback on gaps, missing sections, and recommendations.
        </p>

        {/* Drop Zone */}
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? C.accent : C.border}`,
            borderRadius: 12, padding: "48px 24px",
            textAlign: "center", cursor: "pointer",
            background: dragOver ? C.accentDim + "20" : C.cardAlt,
            transition: "all 0.2s",
            marginBottom: 16
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            style={{ display: "none" }}
          />
          <div style={{ fontSize: 48, marginBottom: 12 }}>📄</div>
          <div style={{ fontSize: 14, fontWeight: 600, color: C.text, marginBottom: 4 }}>
            {dragOver ? "Drop your PDF here" : "Drag & drop your prospectus PDF"}
          </div>
          <div style={{ fontSize: 12, color: C.textMuted, marginBottom: 12 }}>
            or click to browse
          </div>
          <div style={{ fontSize: 11, color: C.textMuted }}>
            PDF only • Max 10MB
          </div>
        </div>

        {/* Selected File */}
        {file && (
          <div style={{
            padding: 12, background: C.cardAlt, borderRadius: 8,
            display: "flex", alignItems: "center", gap: 12,
            marginBottom: 16
          }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              background: C.accentDim + "30",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 18
            }}>📄</div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontSize: 13, fontWeight: 600, color: C.text,
                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis"
              }}>
                {file.name}
              </div>
              <div style={{ fontSize: 11, color: C.textMuted }}>
                {formatFileSize(file.size)}
              </div>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); setError(null); }}
              style={{
                width: 24, height: 24, borderRadius: 4,
                background: C.red + "20", color: C.red,
                border: "none", cursor: "pointer", fontSize: 14,
                display: "flex", alignItems: "center", justifyContent: "center"
              }}
            >
                ×
              </button>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div style={{
            padding: 12, background: C.red + "15", borderRadius: 8,
            border: `1px solid ${C.red + "40"}`, marginBottom: 16
          }}>
            <div style={{ fontSize: 12, color: C.red }}>
              ⚠ {error}
            </div>
          </div>
        )}

        {/* Upload Button */}
        <button
          onClick={handleUpload}
          disabled={!file || loading}
          style={{
            padding: "14px 24px", background: file && !loading ? C.accent : C.cardAlt,
            border: "none", borderRadius: 8, fontWeight: 700, cursor: file && !loading ? "pointer" : "not-allowed",
            fontSize: 14, fontFamily: font, color: file && !loading ? "#000" : C.textMuted,
            opacity: file && !loading ? 1 : 0.6, width: "100%"
          }}
        >
          {loading ? "Analyzing..." : "Analyze Prospectus →"}
        </button>

        {loading && (
          <div style={{ textAlign: "center", marginTop: 12 }}>
            <div style={{ fontSize: 11, color: C.textMuted }}>
              This may take a moment for large documents...
            </div>
          </div>
        )}
      </Card>

      {/* Info Cards */}
      <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
        <Card>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: C.accent }}>
            How It Works
          </div>
          <div style={{ fontSize: 12, color: C.textDim, lineHeight: 1.8 }}>
            <p><strong>1. Upload</strong> your draft prospectus PDF.</p>
            <p><strong>2. AI Analysis</strong> against CMA Kenya requirements.</p>
            <p><strong>3. Get Report</strong> with gaps and recommendations.</p>
          </div>
        </Card>

        <Card>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 12, color: C.blue }}>
            CMA Requirements Checked
          </div>
          <div style={{ fontSize: 11, color: C.textDim, display: "flex", flexDirection: "column", gap: 6 }}>
            <div>✓ Financial Information (3 years audited)</div>
            <div>✓ Business Overview & MD&A</div>
            <div>✓ Corporate Governance</div>
            <div>✓ Offering Details & Use of Proceeds</div>
            <div>✓ Legal & Regulatory Compliance</div>
            <div>✓ Risk Factors (incl. ESG)</div>
          </div>
        </Card>

        <Card style={{ background: C.cardAlt }}>
          <div style={{ fontSize: 11, color: C.textMuted, fontStyle: "italic" }}>
            This tool provides AI-assisted guidance and is not a substitute for professional legal advice. Always consult with qualified securities lawyers before CMA submission.
          </div>
        </Card>
      </div>
    </div>
  );
}
