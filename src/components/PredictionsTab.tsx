import { useState, useEffect } from "react";
import { API_BASE } from "../config/api";

// Theme (shared with HazinaDemo)
const C = {
  bg: "#060B18", card: "#0D1425", cardAlt: "#111D33", border: "#1A2744",
  accent: "#10B981", accentDim: "#065F46", blue: "#3B82F6", blueDim: "#1E3A5F",
  gold: "#F59E0B", purple: "#8B5CF6", red: "#EF4444", cyan: "#06B6D4",
  text: "#F1F5F9", textDim: "#94A3B8", textMuted: "#64748B",
};
const font = "'Segoe UI', system-ui, sans-serif";

// Company names (expanded for all NSE stocks)
const COMPANY_NAMES: Record<string, string> = {
  "SCOM": "Safaricom PLC",
  "EQTY": "Equity Group",
  "KCB": "KCB Group",
  "ABSA": "Absa Bank",
  "EABL": "East African Breweries",
  "BAMB": "Bamburi Cement",
  "COOP": "Cooperative Bank",
  "NMG": "Nation Media Group",
  "JUBH": "Jubilee Holdings",
  "CNTY": "Centum",
  "KAPC": "Kenya Airways",
  "KENG": "KenGen",
  "KNRE": "Kenya Re",
  "TKN": "Telkom Kenya",
  "ARM": "ARM Cement",
  "BAT": "British American Tobacco",
  "BRCK": "Brimstone Investment",
  "LKL": "Liberty Holdings",
  "SPWN": "Spencer Flowers",
  "HAFR": "HF Group",
  "DVSU": "Davis & Shirtliff",
  "FTRE": "Finlease",
  "CFCF": "CFC Stanbic",
  "ICDC": "Investments & Securities",
  "MMMM": "Mumias Sugar",
  "NORE": "Nation Express",
  "DTK": "Diamond Trust Bank",
  "SBSC": "Standard Chartered",
  "HFCK": "Housing Finance",
  "CIC": "CIC Insurance",
  "MSC": "Mobius",
  "UOM": "Uchumi Supermarkets",
  "WTKR": "Total Kenya",
  "LVVR": "Livingstone",
  "SFT": "Sameer Africa",
  "ATLA": "Atlantis",
  "KQL": "Kenya Airways",
  "PORT": "Portsmouth",
  "RMS": "Rms",
  "KP": "Kenol",
  "KAPA": "Kapchorua Tea",
  "LIM": "Limuru Tea",
  "GSU": "Gaara",
  "JUBK": "Jubilee Insurance",
  "KOF": "Koffee",
  "SISL": "Sisal",
  "TEA": "Tea",
  "MTRN": "Motorways",
  "KURV": "Kuria",
  "MOLO": "Molo Tea",
  "UMME": "Umw",
  "REAV": "Real Estate",
  "NSEL": "NSE",
  "APEA": "Apac",
  "CHLL": "Chille",
  "BBK": "Barclays",
  "FAF": "Fidelity",
};

// Components
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

// Direction icons
const DirectionIcon = ({ direction, size = 24 }: { direction: string; size?: number }) => {
  const icons = {
    UP: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 19V5M5 12l7-7 7 7"/></svg>,
    DOWN: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M12 5v14M5 12l7 7 7-7"/></svg>,
    HOLD: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/></svg>,
  };
  return icons[direction as keyof typeof icons] || icons.HOLD;
};

// Confidence bar
const ConfidenceBar = ({ confidence, color }: { confidence: number; color: string }) => (
  <div style={{ width: "100%" }}>
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 10, color: C.textMuted, marginBottom: 4 }}>
      <span>Confidence</span>
      <span style={{ color, fontWeight: 600 }}>{Math.round(confidence * 100)}%</span>
    </div>
    <div style={{ height: 6, background: C.bg, borderRadius: 3, overflow: "hidden" }}>
      <div style={{
        height: "100%",
        width: `${confidence * 100}%`,
        background: color,
        borderRadius: 3,
        transition: "width 0.5s ease"
      }}/>
    </div>
  </div>
);

// Sentiment meter
const SentimentMeter = ({ value, label }: { value: number; label: string }) => {
  const color = value >= 0.6 ? C.accent : value >= 0.4 ? C.gold : C.red;
  const displayValue = Math.round(value * 100);

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <span style={{ fontSize: 10, color: C.textDim }}>{label}</span>
      <div style={{ width: 40, height: 3, background: C.bg, borderRadius: 2, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${displayValue}%`, background: color, borderRadius: 2 }}/>
      </div>
      <span style={{ fontSize: 10, fontWeight: 600, color }}>{displayValue}%</span>
    </div>
  );
};

// Pagination controls
const Pagination = ({ page, totalPages, onPageChange, hasNext, hasPrev }: {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  hasNext: boolean;
  hasPrev: boolean;
}) => (
  <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "center", marginTop: 12 }}>
    <button
      onClick={() => onPageChange(page - 1)}
      disabled={!hasPrev}
      style={{
        padding: "6px 14px", borderRadius: 6, border: `1px solid ${C.border}`,
        background: hasPrev ? C.card : C.bg, color: hasPrev ? C.text : C.textMuted,
        cursor: hasPrev ? "pointer" : "not-allowed", fontSize: 12, fontWeight: 600,
        fontFamily: font, transition: "all 0.2s"
      }}
    >
      ← Prev
    </button>
    <span style={{ fontSize: 13, color: C.text }}>
      Page <span style={{ color: C.accent, fontWeight: 700 }}> {page}</span> / {totalPages}
    </span>
    <button
      onClick={() => onPageChange(page + 1)}
      disabled={!hasNext}
      style={{
        padding: "6px 14px", borderRadius: 6, border: `1px solid ${C.border}`,
        background: hasNext ? C.card : C.bg, color: hasNext ? C.text : C.textMuted,
        cursor: hasNext ? "pointer" : "not-allowed", fontSize: 12, fontWeight: 600,
        fontFamily: font, transition: "all 0.2s"
      }}
    >
      Next →
    </button>
  </div>
);

export default function PredictionsTab() {
  const [predictions, setPredictions] = useState<any[]>([]);
  const [selectedStock, setSelectedStock] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState({ page: 1, page_size: 20, total: 0, total_pages: 1, has_next: false, has_prev: false });
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [hasData, setHasData] = useState(false);

  // Fetch predictions for current page
  useEffect(() => {
    const fetchData = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 3000);

        const response = await fetch(`${API_BASE}/predictions/batch?page=${page}&page_size=6&sort=signal_count`, {
          signal: controller.signal
        });
        clearTimeout(timeoutId);

        if (!response.ok) throw new Error('API unavailable');

        const data = await response.json();

        if (data.predictions && data.predictions.length > 0) {
          setPredictions(data.predictions);
          setPagination(data.pagination || { page: 1, page_size: 20, total: 0, total_pages: 1, has_next: false, has_prev: false });
          setLastUpdated(data.last_updated || data.updated_at || null);
          setHasData(true);
        } else {
          setHasData(false);
        }
      } catch (err) {
        console.error('Error fetching predictions:', err);
        setHasData(false);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [page]);

  // Reset page when changing back to this tab
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    setSelectedStock(null);
  };

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
        <div style={{ color: C.textMuted, fontSize: 14 }}>Loading AI predictions...</div>
      </div>
    );
  }

  if (!hasData) {
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "60vh", gap: 16 }}>
        <div style={{ fontSize: 48, opacity: 0.3 }}>📊</div>
        <div style={{ fontSize: 16, fontWeight: 600 }}>No predictions available</div>
        <div style={{ fontSize: 13, color: C.textMuted, textAlign: "center", maxWidth: 400 }}>
          Run the news scraper and cache update to populate predictions.
        </div>
        <div style={{ fontSize: 11, color: C.textDim, fontFamily: "monospace", padding: "8px 12px", background: C.bg, borderRadius: 4 }}>
          python -m app.services.news_scraper
        </div>
      </div>
    );
  }

  // Calculate stats from current page
  const bullish = predictions.filter((p: any) => {
    const pred7d = p.predictions?.find((pred: any) => pred.horizon_days === 7);
    return pred7d?.direction === "UP";
  }).length;
  const bearish = predictions.filter((p: any) => {
    const pred7d = p.predictions?.find((pred: any) => pred.horizon_days === 7);
    return pred7d?.direction === "DOWN";
  }).length;
  const avgConfidence = predictions.length > 0
    ? Math.round(predictions.reduce((sum: number, p: any) => {
        const pred7d = p.predictions?.find((pred: any) => pred.horizon_days === 7);
        return sum + (pred7d?.confidence || 0);
      }, 0) / predictions.length * 100)
    : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <div style={{ fontSize: 24, fontWeight: 800, marginBottom: 4 }}>AI Price Predictions</div>
          <div style={{ fontSize: 13, color: C.textMuted }}>
            Multi-horizon forecasts for {pagination?.total ?? 0} NSE stocks
            {lastUpdated && (
              <span style={{ color: C.accent, marginLeft: 8 }}>
                · Updated {new Date(lastUpdated).toLocaleDateString([], {month: 'short', day: 'numeric', hour: '2-digit', minute:'2-digit'})}
              </span>
            )}
          </div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <Badge text="3x Daily" color={C.purple} />
        </div>
      </div>

      {/* Stats Row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        <Card glow style={{ padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 10, background: C.accent + "20",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20
            }}>📊</div>
            <div>
              <div style={{ fontSize: 10, color: C.textMuted, textTransform: "uppercase", letterSpacing: 1 }}>Stocks</div>
              <div style={{ fontSize: 22, fontWeight: 800 }}>{pagination?.total ?? 0}</div>
            </div>
          </div>
        </Card>
        <Card style={{ padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 10, background: C.accent + "20",
              display: "flex", alignItems: "center", justifyContent: "center"
            }}><DirectionIcon direction="UP" size={22}/></div>
            <div>
              <div style={{ fontSize: 10, color: C.textMuted, textTransform: "uppercase", letterSpacing: 1 }}>Bullish</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: C.accent }}>{bullish}</div>
            </div>
          </div>
        </Card>
        <Card style={{ padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 10, background: C.red + "20",
              display: "flex", alignItems: "center", justifyContent: "center"
            }}><DirectionIcon direction="DOWN" size={22}/></div>
            <div>
              <div style={{ fontSize: 10, color: C.textMuted, textTransform: "uppercase", letterSpacing: 1 }}>Bearish</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: C.red }}>{bearish}</div>
            </div>
          </div>
        </Card>
        <Card style={{ padding: 16 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{
              width: 44, height: 44, borderRadius: 10, background: C.purple + "20",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20
            }}>🎯</div>
            <div>
              <div style={{ fontSize: 10, color: C.textMuted, textTransform: "uppercase", letterSpacing: 1 }}>Avg Conf</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: C.purple }}>{avgConfidence}%</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Main Content */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 420px", gap: 20 }}>
        {/* Stock List with Pagination */}
        <Card>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.textMuted, textTransform: "uppercase", letterSpacing: 1 }}>
              NSE Stocks
            </div>
            <div style={{ fontSize: 11, color: C.textMuted }}>
              {pagination?.total ?? 0} stocks · Page {pagination?.page ?? 1}/{pagination?.total_pages ?? 1}
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {predictions.map((stock: any, i: number) => {
              const pred7d = stock.predictions?.find((p: any) => p.horizon_days === 7) || stock.predictions?.[0];
              const colors = { UP: C.accent, DOWN: C.red, HOLD: C.gold };
              const color = colors[pred7d?.direction as keyof typeof colors] || C.textDim;
              const isSelected = selectedStock?.symbol === stock.symbol;

              return (
                <div
                  key={i}
                  onClick={() => setSelectedStock(stock)}
                  style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    padding: "12px 14px", borderRadius: 8, background: isSelected ? C.border : C.cardAlt,
                    cursor: "pointer", transition: "all 0.2s",
                    border: isSelected ? `1px solid ${color}` : "1px solid transparent",
                  }}
                >
                  <div style={{ flex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ fontSize: 14, fontWeight: 700 }}>{stock.symbol}</span>
                      <div style={{ display: "flex", alignItems: "center", gap: 4, color }}>
                        <DirectionIcon direction={pred7d?.direction || "HOLD"} size={14}/>
                      </div>
                      <span style={{ fontSize: 10, color: C.textDim, background: C.bg, padding: "2px 6px", borderRadius: 4 }}>
                        {stock.signal_count || 0} signals
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: C.textMuted, marginTop: 3 }}>
                      {COMPANY_NAMES[stock.symbol] || stock.symbol}
                    </div>
                  </div>
                  <div style={{ textAlign: "right", minWidth: 60 }}>
                    <div style={{ fontSize: 18, fontWeight: 800, color }}>{Math.round((pred7d?.confidence || 0) * 100)}%</div>
                    <div style={{ fontSize: 9, color: C.textDim }}>conf</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Pagination */}
          <Pagination
            page={pagination?.page ?? 1}
            totalPages={pagination?.total_pages ?? 1}
            onPageChange={handlePageChange}
            hasNext={pagination?.has_next ?? false}
            hasPrev={pagination?.has_prev ?? false}
          />
        </Card>

        {/* Detail Panel */}
        <Card style={{ display: "flex", flexDirection: "column" }}>
          {selectedStock ? (
            <>
              {/* Header */}
              <div style={{ paddingBottom: 14, borderBottom: `1px solid ${C.border}` }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start", marginBottom: 8 }}>
                  <div>
                    <div style={{ fontSize: 22, fontWeight: 800 }}>{selectedStock.symbol}</div>
                    <div style={{ fontSize: 12, color: C.textMuted }}>
                      {COMPANY_NAMES[selectedStock.symbol] || selectedStock.symbol}
                    </div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: 20, fontWeight: 800 }}>
                      {selectedStock.current_price > 0 ? `KES ${selectedStock.current_price.toFixed(2)}` : "N/A"}
                    </div>
                    <div style={{ fontSize: 10, color: C.textMuted }}>Current Price</div>
                  </div>
                </div>

                {/* Sentiment meters */}
                <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 10 }}>
                  <SentimentMeter value={selectedStock.overall_sentiment || 0} label="Overall" />
                  <SentimentMeter value={selectedStock.news_sentiment || 0} label="News" />
                  <SentimentMeter value={selectedStock.twitter_sentiment || 0} label="Twitter" />
                </div>
              </div>

              {/* Timeline */}
              <div style={{ padding: "16px 0" }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: C.textMuted, marginBottom: 12, textTransform: "uppercase", letterSpacing: 1 }}>
                  Price Forecast Timeline
                </div>

                <div style={{ position: "relative", paddingLeft: 24 }}>
                  {/* Timeline line */}
                  <div style={{
                    position: "absolute", left: 7, top: 12, bottom: 12,
                    width: 2, background: C.border, borderRadius: 1
                  }}/>

                  {selectedStock.predictions?.map((pred: any, i: number) => {
                    const colors = { UP: C.accent, DOWN: C.red, HOLD: C.gold };
                    const color = colors[pred.direction as keyof typeof colors] || C.textDim;

                    return (
                      <div key={i} style={{ marginBottom: i < 2 ? 14 : 0, position: "relative" }}>
                        {/* Timeline dot */}
                        <div style={{
                          position: "absolute", left: -20, top: 12,
                          width: 12, height: 12, borderRadius: "50%",
                          background: color, border: `3px solid ${C.card}`,
                          zIndex: 1
                        }}/>

                        <div style={{
                          padding: 14, borderRadius: 10, background: C.bg,
                          border: `1px solid ${color}30`,
                        }}>
                          {/* Top row: direction + confidence */}
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <div style={{ color, display: "flex", alignItems: "center", gap: 6 }}>
                                <DirectionIcon direction={pred.direction} size={18} />
                                <span style={{ fontSize: 14, fontWeight: 700 }}>{pred.direction}</span>
                              </div>
                              <span style={{
                                fontSize: 18, fontWeight: 800, color,
                                background: color + "15", padding: "2px 10px", borderRadius: 6
                              }}>{pred.horizon_days}d</span>
                            </div>
                            <div style={{ fontSize: 20, fontWeight: 800, color }}>{Math.round(pred.confidence * 100)}<span style={{ fontSize: 12, color: C.textDim, fontWeight: 500 }}>%</span></div>
                          </div>

                          {/* Confidence bar */}
                          <ConfidenceBar confidence={pred.confidence} color={color} />

                          {/* Reasoning */}
                          <div style={{
                            marginTop: 10, padding: 10, borderRadius: 6,
                            background: C.cardAlt, fontSize: 11,
                            color: C.textDim, lineHeight: 1.5
                          }}>
                            💡 {pred.reasoning}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Footer */}
              <div style={{ marginTop: "auto", paddingTop: 12, borderTop: `1px solid ${C.border}` }}>
                <div style={{ fontSize: 10, color: C.textMuted, textAlign: "center" }}>
                  Based on {selectedStock.signal_count || 0} sentiment signals
                </div>
              </div>
            </>
          ) : (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: C.textMuted }}>
              <div style={{
                width: 64, height: 64, borderRadius: 16, background: C.cardAlt,
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: 28, marginBottom: 12
              }}>📈</div>
              <div style={{ fontSize: 14 }}>Select a stock</div>
              <div style={{ fontSize: 11, color: C.textDim, marginTop: 2 }}>View AI price predictions</div>
            </div>
          )}
        </Card>
      </div>

      {/* Disclaimer */}
      <div style={{
        padding: 12, borderRadius: 8, background: C.cardAlt,
        fontSize: 11, color: C.textMuted, lineHeight: 1.5,
        border: `1px solid ${C.gold}30`
      }}>
        <strong style={{ color: C.gold }}>⚠ Disclaimer:</strong> AI predictions are for informational purposes only and should not be considered financial advice.
        Always conduct your own research before making investment decisions.
      </div>
    </div>
  );
}
