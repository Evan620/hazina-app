import { useState, useEffect } from "react";
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import ListingScannerTab from "./components/ListingScannerTab";
import ProspectusCheckerTab from "./components/ProspectusCheckerTab";
import PredictionsTab from "./components/PredictionsTab";
import { API_BASE } from "./config/api";

// ─── THEME ───
const C = {
  bg: "#060B18", card: "#0D1425", cardAlt: "#111D33", border: "#1A2744",
  accent: "#10B981", accentDim: "#065F46", blue: "#3B82F6", blueDim: "#1E3A5F",
  gold: "#F59E0B", purple: "#8B5CF6", red: "#EF4444", cyan: "#06B6D4",
  text: "#F1F5F9", textDim: "#94A3B8", textMuted: "#64748B",
};

const font = "'Segoe UI', system-ui, sans-serif";

// ─── DATA ───
const acquisitionData = [
  { q: "Q2 '26", ziidi: 85, hazina: 85, diaspora: 0 },
  { q: "Q3 '26", ziidi: 140, hazina: 195, diaspora: 12 },
  { q: "Q4 '26", ziidi: 210, hazina: 380, diaspora: 45 },
  { q: "Q1 '27", ziidi: 290, hazina: 620, diaspora: 95 },
  { q: "Q2 '27", ziidi: 380, hazina: 950, diaspora: 180 },
  { q: "Q3 '27", ziidi: 480, hazina: 1400, diaspora: 310 },
];

const revenueData = [
  { src: "Trading Commissions", now: 340, proj: 890 },
  { src: "Data & Analytics", now: 45, proj: 280 },
  { src: "Diaspora Corridor", now: 0, proj: 420 },
  { src: "Premium Subs", now: 0, proj: 180 },
  { src: "Listing Pipeline", now: 180, proj: 350 },
  { src: "Education", now: 12, proj: 85 },
];

// Company name mapping for NSE symbols
const COMPANY_NAMES: Record<string, string> = {
  "SCOM": "Safaricom PLC",
  "EQTY": "Equity Group Holdings",
  "KCB": "KCB Group",
  "ABSA": "Absa Bank Kenya",
  "EABL": "East African Breweries",
  "BAMB": "Bamburi Cement",
  "COOP": "Cooperative Bank",
  "NMG": "Nation Media Group",
  "JUBH": "Jubilee Holdings",
  "CNTY": "Centum Investment",
  "KAPC": "Kenya Airways",
  "KENG": "KenGen",
  "TKN": "Telkom Kenya",
  "BAT": "British American Tobacco",
  "ARM": "ARM Cement",
  "BRCK": "Brimstone Investment",
  "LKL": "Liberty Holdings",
  "SPWN": "Spencer Flowers",
  "WTKR": "Walters Kenya",
  "KNRE": "Kenya Re",
};

// Demo fallback data (used when API unavailable)
const demoRecommendations = [
  { ticker: "SCOM", name: "Safaricom PLC", action: "BUY", conf: 85, reason: "Strong M-Pesa growth, 5G rollout catalyst", price: "KES 38.50", sector: "Telecom", changePercent: 1.2, priceChange: "+1.2%" },
  { ticker: "EQTY", name: "Equity Group", action: "HOLD", conf: 62, reason: "Regional expansion on track but margin pressure", price: "KES 52.75", sector: "Banking", changePercent: -0.3, priceChange: "-0.3%" },
  { ticker: "KCB", name: "KCB Group", action: "BUY", conf: 78, reason: "Q3 earnings beat expectations", price: "KES 18.20", sector: "Banking", changePercent: 0.8, priceChange: "+0.8%" },
  { ticker: "ABSA", name: "Absa Bank", action: "BUY", conf: 70, reason: "Consumer finance unit growth", price: "KES 14.50", sector: "Banking", changePercent: 0.5, priceChange: "+0.5%" },
];

const diaspora = [
  { country: "🇺🇸 United States", flow: "$2.73B", investors: "45,200", growth: "+34%" },
  { country: "🇬🇧 United Kingdom", flow: "$680M", investors: "18,400", growth: "+28%" },
  { country: "🇦🇪 UAE / Gulf", flow: "$410M", investors: "8,900", growth: "+41%" },
  { country: "🇨🇦 Canada", flow: "$290M", investors: "6,200", growth: "+22%" },
  { country: "🇩🇪 Germany", flow: "$180M", investors: "3,800", growth: "+19%" },
];

const education = [
  { title: "What is the NSE?", level: "Beginner", dur: "5 min", prog: 100, icon: "🏛️" },
  { title: "Understanding Share Prices", level: "Beginner", dur: "8 min", prog: 100, icon: "📊" },
  { title: "Reading Financial Statements", level: "Intermediate", dur: "15 min", prog: 45, icon: "📋" },
  { title: "Dividend Investing Strategy", level: "Intermediate", dur: "12 min", prog: 0, icon: "💰" },
  { title: "ETFs & Index Funds on NSE", level: "Beginner", dur: "10 min", prog: 0, icon: "📈" },
  { title: "Diaspora Investment Tax Guide", level: "Advanced", dur: "20 min", prog: 0, icon: "🌍" },
];

const chatMessages = [
  { role: "user", text: "I'm a Kenyan living in Texas. I want to invest $500/month back home but I don't have M-Pesa. What are my options?" },
  { role: "ai", text: "Welcome! Through Hazina's diaspora gateway, you can invest directly in NSE-listed securities without M-Pesa.\n\n📋 Onboarding: Video KYC using your Kenyan passport + US driver's license. ~10 minutes.\n\n💰 Funding: Direct ACH transfer from your US bank. Batched wholesale FX rates — saving ~6% vs typical remittance.\n\n🎯 For $500/month, I'd recommend:\n• 40% — Safaricom (stable dividends, 5.8% yield)\n• 30% — NSE 25 ETF (diversified exposure)\n• 20% — KPC (infrastructure growth play)\n• 10% — Hazina Diaspora Bond Fund (tokenized, AUDA-NEPAD backed)\n\nShall I set up your account?" },
  { role: "user", text: "What about taxes? I don't want double taxation." },
  { role: "ai", text: "Smart question. No Kenya-US DTA exists — but there are legal strategies:\n\n1. Withholding tax: Kenya charges 15% on dividends for non-residents. This is your final tax in Kenya.\n\n2. US Foreign Tax Credit: You can claim the Kenyan withholding tax as a credit on IRS Form 1116, effectively avoiding double taxation on dividends.\n\n3. Capital gains: Kenya exempts listed securities from capital gains tax for non-residents. Your US obligation depends on holding period.\n\nHazina auto-generates your tax summary for both jurisdictions at year-end." },
];

const pieData = [
  { name: "Trading", value: 41, color: C.accent },
  { name: "Data", value: 13, color: C.blue },
  { name: "Diaspora", value: 19, color: C.gold },
  { name: "Subs", value: 8, color: C.purple },
  { name: "Listing", value: 16, color: C.cyan },
  { name: "Education", value: 3, color: C.red },
];

// ─── COMPONENTS ───
const Card = ({ children, style, glow }: { children: React.ReactNode; style?: React.CSSProperties; glow?: boolean }) => (
  <div style={{
    background: C.card, borderRadius: 12, padding: 20,
    border: `1px solid ${glow ? C.accent + "40" : C.border}`,
    boxShadow: glow ? `0 0 20px ${C.accent}15` : "none",
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

const Stat = ({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) => (
  <div style={{ textAlign: "center" }}>
    <div style={{ fontSize: 11, color: C.textMuted, textTransform: "uppercase", letterSpacing: 1, marginBottom: 4, fontFamily: font }}>{label}</div>
    <div style={{ fontSize: 28, fontWeight: 800, color: color || C.text, fontFamily: font }}>{value}</div>
    {sub && <div style={{ fontSize: 11, color: C.accent, marginTop: 2, fontFamily: font }}>{sub}</div>}
  </div>
);

const tabs = ["Dashboard", "AI Price Predictions", "AI Advisor", "Listing Scanner", "Prospectus Checker", "Diaspora", "Education", "Revenue Impact"];

export default function Hazina() {
  const [tab, setTab] = useState(0);

  return (
    <div style={{ minHeight: "100vh", background: C.bg, color: C.text, fontFamily: font }}>
      {/* HEADER */}
      <div style={{ position: "sticky", top: 0, zIndex: 100, padding: "16px 24px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 16, background: C.bg }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: `linear-gradient(135deg, ${C.accent}, ${C.blue})`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 18, fontWeight: 900, color: "#fff",
          }}>H</div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 800, letterSpacing: -0.5 }}>HAZINA</div>
            <div style={{ fontSize: 10, color: C.textMuted, letterSpacing: 2, textTransform: "uppercase" }}>Powered by AfCEN</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 2, marginLeft: 32 }}>
          {tabs.map((t, i) => (
            <button key={i} onClick={() => setTab(i)} style={{
              padding: "8px 16px", border: "none", borderRadius: 8, cursor: "pointer",
              fontSize: 13, fontWeight: tab === i ? 700 : 500, fontFamily: font,
              background: tab === i ? C.accent + "20" : "transparent",
              color: tab === i ? C.accent : C.textDim,
              transition: "all 0.2s",
            }}>{t}</button>
          ))}
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
          <Badge text="DEMO" color={C.gold} />
          <div style={{ fontSize: 12, color: C.textMuted }}>NSE Partnership Preview</div>
        </div>
      </div>

      {/* CONTENT */}
      <div style={{ padding: "24px 32px", maxWidth: 1600, margin: "0 auto" }}>
        {tab === 0 && <DashboardTab />}
        {tab === 1 && <PredictionsTab />}
        {tab === 2 && <AdvisorTab />}
        {tab === 3 && <ListingScannerTab />}
        {tab === 4 && <ProspectusCheckerTab />}
        {tab === 5 && <DiasporaTab />}
        {tab === 6 && <EducationTab />}
        {tab === 7 && <RevenueTab />}
      </div>
    </div>
  );
}

// ─── DASHBOARD ───
function DashboardTab() {
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [usingDemo, setUsingDemo] = useState(false);

  // Fetch sentiment signals from backend
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [sentimentResponse, pricesResponse] = await Promise.all([
          fetch(`${API_BASE}/sentiment/signals?limit=10`),
          fetch(`${API_BASE}/market/prices`)
        ]);

        if (!sentimentResponse.ok) throw new Error('Sentiment API unavailable');
        if (!pricesResponse.ok) throw new Error('Prices API unavailable');

        const sentimentData = await sentimentResponse.json();
        const pricesData = await pricesResponse.json();

        // Store prices for lookup
        const priceMap: Record<string, any> = {};
        pricesData.prices.forEach((p: any) => {
          priceMap[p.symbol] = p;
        });

        // Transform sentiment signals to recommendations format
        const transformed = sentimentData.signals.map((s: any) => {
          const action = s.overall_sentiment === 'bullish' ? 'BUY' :
                         s.overall_sentiment === 'bearish' ? 'SELL' : 'HOLD';
          const reason = s.signals?.[0]?.reason || 'Market sentiment analysis';
          const confidence = Math.round(s.avg_confidence * 100);

          // Get price from price map
          const priceData = priceMap[s.symbol];
          const price = priceData?.price || 0;
          const changePercent = priceData?.change_percent || 0;

          return {
            ticker: s.symbol,
            name: COMPANY_NAMES[s.symbol] || s.symbol,
            action,
            conf: confidence,
            reason,
            price: price > 0 ? `KES ${price.toFixed(2)}` : "N/A",
            sector: "NSE",
            changePercent: changePercent,
            priceChange: priceData?.formatted_change || ""
          };
        });

        setRecommendations(transformed);
        setUsingDemo(false);
      } catch (err) {
        console.warn('Using demo data (backend unavailable):', err);
        setRecommendations(demoRecommendations);
        setUsingDemo(true);
      } finally {
        setLoading(false);
      }
    };

    fetchData();

    // Refresh prices every 60 seconds
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
        <Card glow><Stat label="Active Investors" value="1.4M" sub="↑ 312% with Hazina" color={C.accent} /></Card>
        <Card><Stat label="Diaspora Investors" value="310K" sub="New channel" color={C.blue} /></Card>
        <Card><Stat label="NSE Revenue" value="KES 2.2B" sub="↑ from KES 828M" color={C.gold} /></Card>
        <Card><Stat label="Live Signals" value={loading ? "..." : String(recommendations.length)} sub={usingDemo ? "Demo mode" : "News sentiment"} color={C.purple} /></Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 0.7fr", gap: 20 }}>
        {/* Acquisition chart */}
        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>Investor Acquisition Projection</div>
          <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 16 }}>Thousands of active investors — Ziidi alone vs. Ziidi + Hazina</div>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={acquisitionData}>
              <defs>
                <linearGradient id="gH" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={C.accent} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={C.accent} stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gD" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={C.blue} stopOpacity={0.3} />
                  <stop offset="100%" stopColor={C.blue} stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="q" tick={{ fill: C.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: C.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}K`} />
              <Tooltip contentStyle={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 12, color: C.text }} />
              <Area type="monotone" dataKey="hazina" name="With Hazina" stroke={C.accent} fill="url(#gH)" strokeWidth={2} />
              <Area type="monotone" dataKey="diaspora" name="Diaspora" stroke={C.blue} fill="url(#gD)" strokeWidth={2} />
              <Area type="monotone" dataKey="ziidi" name="Ziidi Only" stroke={C.textMuted} fill="none" strokeWidth={1.5} strokeDasharray="4 4" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        {/* Sentiment Signals */}
        <Card style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 700 }}>Market Signals</div>
            <div style={{ display: "flex", gap: 6 }}>
              {usingDemo && <Badge text="DEMO" color={C.gold} />}
              <Badge text="Live" color={C.accent} />
            </div>
          </div>
          {loading ? (
            <div style={{ padding: 20, textAlign: 'center', color: C.textMuted, fontSize: 13 }}>Loading signals...</div>
          ) : recommendations.length === 0 ? (
            <div style={{ padding: 20, textAlign: 'center', color: C.textMuted, fontSize: 13 }}>No signals available. Run scraper first.</div>
          ) : (
            <div style={{ maxHeight: 280, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
              {recommendations.slice(0, 6).map((r, i) => (
                <div key={i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "10px 12px", borderRadius: 8, background: C.cardAlt,
                }}>
                  <div style={{ textAlign: "left", flex: 1 }}>
                    <div style={{ fontSize: 13, fontWeight: 700 }}>{r.ticker}</div>
                    <div style={{ fontSize: 10, color: C.textMuted }}>
                      {r.price} {r.priceChange && `· ${r.priceChange}`}
                    </div>
                  </div>
                  <div style={{ textAlign: "right", flexShrink: 0, marginLeft: 12 }}>
                    <Badge text={r.action} color={r.action === "BUY" ? C.accent : r.action === "SELL" ? C.red : C.gold} />
                    <div style={{ fontSize: 10, color: C.textDim, marginTop: 2 }}>{r.conf}%</div>
                  </div>
                </div>
              ))}
            </div>
          )}
          <div style={{ marginTop: "auto", paddingTop: 12, borderTop: `1px solid ${C.border}`, textAlign: "center" }}>
            <div style={{ fontSize: 11, color: C.textMuted }}>
              View <span style={{ color: C.accent, cursor: "pointer" }}>AI Price Predictions</span> for detailed forecasts
            </div>
          </div>
        </Card>
      </div>

      {/* Bottom cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        <Card glow>
          <div style={{ fontSize: 11, color: C.accent, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Weekly Digest</div>
          <div style={{ fontSize: 13, lineHeight: 1.6 }}>
            <strong>NSE rallied 3.2% this week</strong> driven by banking sector earnings beats. Your portfolio outperformed by 1.8%. Three new recommendations generated.
          </div>
          <div style={{ fontSize: 10, color: C.textMuted, marginTop: 8 }}>Delivered Monday 7:00 AM EAT via WhatsApp</div>
        </Card>
        <Card>
          <div style={{ fontSize: 11, color: C.gold, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Risk Alert</div>
          <div style={{ fontSize: 13, lineHeight: 1.6 }}>
            Portfolio <strong>68% concentrated in banking</strong>. Consider diversifying into manufacturing or agriculture ETFs to reduce sector risk.
          </div>
        </Card>
        <Card>
          <div style={{ fontSize: 11, color: C.blue, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Learning Prompt</div>
          <div style={{ fontSize: 13, lineHeight: 1.6 }}>
            Complete <strong>"Reading Financial Statements"</strong> before EQTY reports Q1 results on April 22 for a more informed decision.
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── AI ADVISOR ───
function AdvisorTab() {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 20, minHeight: 520 }}>
      <Card style={{ display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16, paddingBottom: 12, borderBottom: `1px solid ${C.border}` }}>
          <div style={{
            width: 36, height: 36, borderRadius: "50%",
            background: `linear-gradient(135deg, ${C.accent}, ${C.blue})`,
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18,
          }}>🧠</div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700 }}>Hazina AI Advisor</div>
            <div style={{ fontSize: 11, color: C.accent }}>Powered by AfCEN InvestorIQ</div>
          </div>
          <div style={{ marginLeft: "auto" }}><Badge text="Swahili · English · Sheng" color={C.blue} /></div>
        </div>
        <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 12 }}>
          {chatMessages.map((m, i) => (
            <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
              <div style={{
                maxWidth: "82%", padding: "12px 16px",
                borderRadius: m.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                background: m.role === "user" ? C.blue : C.accentDim + "60",
                fontSize: 13, lineHeight: 1.65, whiteSpace: "pre-wrap",
              }}>{m.text}</div>
            </div>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 14, paddingTop: 12, borderTop: `1px solid ${C.border}` }}>
          <input placeholder="Ask about any NSE stock, your portfolio, or investment strategy..." style={{
            flex: 1, padding: "10px 14px", background: C.bg, border: `1px solid ${C.border}`,
            borderRadius: 8, color: C.text, fontSize: 13, outline: "none", fontFamily: font,
          }} />
          <button style={{
            padding: "10px 20px", background: C.accent, color: "#000", border: "none",
            borderRadius: 8, fontWeight: 700, fontSize: 13, cursor: "pointer", fontFamily: font,
          }}>Send</button>
        </div>
      </Card>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <Card glow>
          <div style={{ fontSize: 11, color: C.accent, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>Advisor Capabilities</div>
          {["Personalized stock picks with confidence scores", "Multilingual: Swahili, English, Sheng + voice", "Tax advisory across Kenya + diaspora jurisdictions", "Portfolio risk assessment & rebalancing", "Real-time market sentiment analysis", "WhatsApp delivery at 7 AM EAT"].map((t, i) => (
            <div key={i} style={{ fontSize: 12, color: C.textDim, padding: "6px 0", borderBottom: i < 5 ? `1px solid ${C.border}` : "none" }}>✦ {t}</div>
          ))}
        </Card>
        <Card>
          <div style={{ fontSize: 11, color: C.gold, textTransform: "uppercase", letterSpacing: 1, marginBottom: 8 }}>5 Signal Layers</div>
          {["Technical analysis — all 67 NSE equities", "Kenyan news sentiment (NLP)", "Macro factors (CBK rates, KES/USD)", "Individual portfolio composition", "Global context & correlations"].map((t, i) => (
            <div key={i} style={{ fontSize: 12, color: C.textDim, padding: "6px 0", display: "flex", gap: 6 }}>
              <span style={{ color: C.gold, fontWeight: 700 }}>{i + 1}.</span> {t}
            </div>
          ))}
        </Card>
      </div>
    </div>
  );
}

// ─── DIASPORA ───
function DiasporaTab() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
        <Card glow><Stat label="Total Diaspora AUM" value="$4.3B" sub="Annualized flow" color={C.accent} /></Card>
        <Card><Stat label="Active Corridors" value="5" sub="US, UK, UAE, CA, DE" color={C.blue} /></Card>
        <Card><Stat label="Avg Remittance Saving" value="6.35%" sub="9.15% → 2.8%" color={C.gold} /></Card>
        <Card><Stat label="Bond Fund Min" value="$50" sub="Tokenized via KDX" color={C.purple} /></Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 20 }}>
        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Diaspora Investment Corridors</div>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                {["Corridor", "Annual Flow", "Investors", "Growth"].map(h => (
                  <th key={h} style={{ textAlign: "left", padding: "8px 12px", fontSize: 11, color: C.textMuted, textTransform: "uppercase", letterSpacing: 0.5 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {diaspora.map((d, i) => (
                <tr key={i} style={{ borderBottom: `1px solid ${C.border}20` }}>
                  <td style={{ padding: "10px 12px", fontWeight: 600 }}>{d.country}</td>
                  <td style={{ padding: "10px 12px" }}>{d.flow}</td>
                  <td style={{ padding: "10px 12px" }}>{d.investors}</td>
                  <td style={{ padding: "10px 12px", color: C.accent, fontWeight: 600 }}>{d.growth}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Hazina Diaspora Bond Fund</div>
          <div style={{ fontSize: 13, color: C.textDim, lineHeight: 1.7, marginBottom: 16 }}>
            Tokenized collective investment vehicle listed on KDX that aggregates diaspora capital at a <strong style={{ color: C.gold }}>$50 minimum</strong> into NSE-listed infrastructure securities.
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              ["Institutional Anchor", "AUDA-NEPAD MoU"],
              ["Tokenization", "KDX Digital Exchange"],
              ["KYC", "Video KYC (10 min)"],
              ["Funding Rails", "ACH / SEPA / Faster Payments"],
              ["FX Routing", "Batched wholesale rates"],
              ["Replication", "15+ AELP exchanges"],
            ].map(([k, v], i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: `1px solid ${C.border}20`, fontSize: 12 }}>
                <span style={{ color: C.textMuted }}>{k}</span>
                <span style={{ color: C.accent, fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 8 }}>Onboarding Flow</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12, marginTop: 12 }}>
          {[
            { step: "1", title: "Video KYC", desc: "Kenyan passport + local ID", time: "10 min" },
            { step: "2", title: "CDS Account", desc: "Auto-opened via NSE API", time: "Instant" },
            { step: "3", title: "Fund Account", desc: "ACH / SEPA / wire", time: "1-2 days" },
            { step: "4", title: "Risk Profile", desc: "AI-guided assessment", time: "5 min" },
            { step: "5", title: "First Trade", desc: "AI recommendation + execute", time: "< 1 min" },
          ].map((s, i) => (
            <div key={i} style={{ textAlign: "center", padding: 16, background: C.cardAlt, borderRadius: 10, position: "relative" }}>
              <div style={{ width: 28, height: 28, borderRadius: "50%", background: C.accent, color: "#000", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 800, fontSize: 13, margin: "0 auto 8px" }}>{s.step}</div>
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 4 }}>{s.title}</div>
              <div style={{ fontSize: 11, color: C.textMuted }}>{s.desc}</div>
              <div style={{ fontSize: 10, color: C.accent, marginTop: 6 }}>{s.time}</div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── EDUCATION ───
function EducationTab() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        <Card glow><Stat label="Learning Score" value="67/100" sub="Complete 3 modules to reach 80" color={C.accent} /></Card>
        <Card><Stat label="Modules Completed" value="2/6" sub="5 hrs total content" color={C.blue} /></Card>
        <Card><Stat label="Trading Confidence" value="Medium" sub="↑ with each module" color={C.gold} /></Card>
      </div>

      <Card>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Adaptive Learning Pathway</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
          {education.map((e, i) => (
            <div key={i} style={{
              display: "flex", alignItems: "center", gap: 14, padding: 14, borderRadius: 10,
              background: C.cardAlt, border: e.prog === 100 ? `1px solid ${C.accent}30` : `1px solid ${C.border}`,
            }}>
              <div style={{ fontSize: 28 }}>{e.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 3 }}>{e.title}</div>
                <div style={{ fontSize: 11, color: C.textMuted }}>{e.level} · {e.dur}</div>
                <div style={{ marginTop: 6, height: 4, borderRadius: 2, background: C.border }}>
                  <div style={{ height: "100%", borderRadius: 2, width: `${e.prog}%`, background: e.prog === 100 ? C.accent : C.blue, transition: "width 0.5s" }} />
                </div>
              </div>
              <div style={{ fontSize: 12, fontWeight: 700, color: e.prog === 100 ? C.accent : C.textMuted }}>
                {e.prog === 100 ? "✓" : `${e.prog}%`}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Gamification</div>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            {[
              { badge: "🏅", name: "First Trade", earned: true },
              { badge: "📚", name: "Scholar", earned: true },
              { badge: "🌍", name: "Diaspora Pioneer", earned: false },
              { badge: "💎", name: "Diamond Hands", earned: false },
              { badge: "🧠", name: "Market Sage", earned: false },
            ].map((b, i) => (
              <div key={i} style={{
                textAlign: "center", padding: 12, borderRadius: 10, width: 80,
                background: b.earned ? C.accentDim + "40" : C.cardAlt,
                opacity: b.earned ? 1 : 0.5,
              }}>
                <div style={{ fontSize: 28, marginBottom: 4 }}>{b.badge}</div>
                <div style={{ fontSize: 10, color: b.earned ? C.accent : C.textMuted }}>{b.name}</div>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Chama Integration</div>
          <div style={{ fontSize: 13, color: C.textDim, lineHeight: 1.7 }}>
            Group investment clubs (chamas) can onboard as a unit, with shared portfolios, collective learning dashboards, and group savings targets. Hazina adapts education content for group settings — perfect for Kenya's 300,000+ active chamas.
          </div>
        </Card>
      </div>
    </div>
  );
}

// ─── REVENUE ───
function RevenueTab() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
        <Card glow><Stat label="Current NSE Revenue" value="KES 828M" sub="FY2024" color={C.textDim} /></Card>
        <Card glow><Stat label="Projected with Hazina" value="KES 2.2B" sub="By FY2027" color={C.accent} /></Card>
        <Card glow><Stat label="Revenue Uplift" value="+166%" sub="New lines: 60% non-trading" color={C.gold} /></Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 20 }}>
        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Revenue by Source — Current vs. Projected (KES M)</div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={revenueData} layout="vertical" barGap={4}>
              <XAxis type="number" tick={{ fill: C.textMuted, fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="src" width={120} tick={{ fill: C.textDim, fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 12, color: C.text }} />
              <Bar dataKey="now" name="Current" fill={C.textMuted} barSize={14} radius={[0, 4, 4, 0]} />
              <Bar dataKey="proj" name="Projected" fill={C.accent} barSize={14} radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card>
          <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Projected Revenue Mix (2027)</div>
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={pieData} innerRadius={50} outerRadius={80} dataKey="value" paddingAngle={3}>
                {pieData.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Pie>
              <Tooltip contentStyle={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 8, fontSize: 12, color: C.text }} />
            </PieChart>
          </ResponsiveContainer>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", marginTop: 8 }}>
            {pieData.map((d, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11 }}>
                <div style={{ width: 8, height: 8, borderRadius: 2, background: d.color }} />
                <span style={{ color: C.textMuted }}>{d.name} {d.value}%</span>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card>
        <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 12 }}>Investment Required</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          {[
            { phase: "Phase 1 — MVP", cost: "$300–475K", time: "6 months", team: "4 people", milestone: "Data vendor agreement + sentiment MVP" },
            { phase: "Phase 2 — Scale", cost: "$500–800K", time: "12 months", team: "8 people", milestone: "Listing intelligence + enterprise API" },
            { phase: "Phase 3 — Pan-African", cost: "$600–925K", time: "12 months", team: "12 people", milestone: "AELP replication + Bond Fund" },
          ].map((p, i) => (
            <div key={i} style={{ padding: 16, background: C.cardAlt, borderRadius: 10 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: C.accent, marginBottom: 8 }}>{p.phase}</div>
              <div style={{ fontSize: 22, fontWeight: 800, marginBottom: 4 }}>{p.cost}</div>
              <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 2 }}>{p.time} · {p.team}</div>
              <div style={{ fontSize: 11, color: C.textDim, marginTop: 8, paddingTop: 8, borderTop: `1px solid ${C.border}` }}>{p.milestone}</div>
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16, padding: 14, background: C.accentDim + "30", borderRadius: 8, fontSize: 13, color: C.accent, fontWeight: 600, textAlign: "center" }}>
          Break-even at month 14–18 · Total: $1.4–2.2M over 30 months · Designed for pan-African replication across 15+ AELP exchanges
        </div>
      </Card>
    </div>
  );
}
