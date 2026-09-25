import { useEffect, useMemo, useState } from "react";
import { ChartPanel } from "./components/ChartPanel";
import { defaultOverlays, type OverlayFlags } from "./chart/overlay";
import { loadSeries, type HistoryRange, type QuoteSeries } from "./data/yahoo";
import { analyzeCached } from "./engine";
import type { PivotStrength } from "./types";

const WATCHLIST = ["PLTR", "MU", "ZS", "TEM", "FPS", "META", "RKLB", "GOOG", "ISRG", "NEE", "UNH", "STIM"];
const STRENGTHS: PivotStrength[] = [3, 5, 10, 20];

export function App() {
  const [page, setPage] = useState<"trading" | "budget">("trading");
  const [symbol, setSymbol] = useState("META");
  const [query, setQuery] = useState("META");
  const [range, setRange] = useState<HistoryRange>("5y");
  const [strength, setStrength] = useState<PivotStrength>(5);
  const [mode, setMode] = useState<"candle" | "heikin">("heikin");
  const [overlays, setOverlays] = useState<OverlayFlags>(defaultOverlays);
  const [series, setSeries] = useState<QuoteSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [stars, setStars] = useState<string[]>(() => ["META"]);
  const [cash] = useState(20000);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    loadSeries(symbol, range)
      .then((next) => {
        if (!cancelled) setSeries(next);
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "โหลดข้อมูลไม่สำเร็จ");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol, range]);

  const analysis = useMemo(
    () => (series ? analyzeCached(series.candles, series.symbol, { pivotStrength: strength }) : null),
    [series, strength],
  );

  const openSymbol = (next: string) => {
    const clean = next.trim().toUpperCase();
    if (!clean) return;
    setSymbol(clean);
    setQuery(clean);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">L</span>
          <div>
            <strong>LELO</strong>
            <small>หุ้น · กราฟ · วิเคราะห์</small>
          </div>
        </div>
        <nav>
          <button className={page === "trading" ? "active" : ""} onClick={() => setPage("trading")}>Trading</button>
          <button className={page === "budget" ? "active" : ""} onClick={() => setPage("budget")}>Budget & Portfolio</button>
          <button onClick={() => exportAnalysis(series, analysis)}>Export</button>
          <label className="import">
            Import
            <input
              type="file"
              accept="application/json"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (!file) return;
                void file.text().then((text) => {
                  const payload = JSON.parse(text) as { symbol?: string };
                  if (payload.symbol) openSymbol(payload.symbol);
                });
              }}
            />
          </label>
        </nav>
        <form
          className="search"
          onSubmit={(event) => {
            event.preventDefault();
            openSymbol(query);
          }}
        >
          <input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="ค้นหาสัญลักษณ์" />
        </form>
        <div className="balance">
          <span>กันยายน 2569</span>
          <strong>คงเหลือ {cash.toLocaleString("th-TH", { minimumFractionDigits: 2 })} บาท</strong>
        </div>
        <div className="symbol-chip">
          <b>{series?.symbol ?? symbol}</b>
          <small>{series?.name ?? ""}</small>
        </div>
      </header>

      {page === "budget" ? (
        <section className="budget">
          <h2>Budget & Portfolio</h2>
          <p>เงินสดจำลอง {cash.toLocaleString("th-TH")} บาท ใช้ดูพอร์ตในเครื่องนี้เท่านั้น ไม่เชื่อมโบรกเกอร์ และไม่ใช่คำแนะนำการลงทุน</p>
        </section>
      ) : (
        <main>
          <div className="watchlist">
            <span>Quick Watchlist</span>
            {WATCHLIST.map((item) => (
              <button key={item} className={item === symbol ? "on" : ""} onClick={() => openSymbol(item)}>
                {item}
                <i
                  onClick={(event) => {
                    event.stopPropagation();
                    setStars((current) => (current.includes(item) ? current.filter((star) => star !== item) : [...current, item]));
                  }}
                >
                  {stars.includes(item) ? "★" : "☆"}
                </i>
              </button>
            ))}
          </div>

          <section className="workspace">
            <div className="chart-column">
              <div className="quote-row">
                <h1>
                  {series?.symbol ?? symbol}
                  <button
                    className="star"
                    onClick={() => setStars((current) => (current.includes(symbol) ? current.filter((item) => item !== symbol) : [...current, symbol]))}
                  >
                    {stars.includes(symbol) ? "★" : "☆"}
                  </button>
                  <em>{series ? `$${series.price.toFixed(2)}` : "--"}</em>
                  <b className={series && series.change >= 0 ? "up" : "down"}>
                    {series ? `${series.change >= 0 ? "+" : ""}${series.changePercent.toFixed(2)}%` : ""}
                  </b>
                </h1>
                <div className="controls">
                  {(["1y", "2y", "5y", "10y"] as HistoryRange[]).map((item) => (
                    <button key={item} className={range === item ? "on" : ""} onClick={() => setRange(item)}>{item.toUpperCase()}</button>
                  ))}
                  <button className={mode === "candle" ? "on" : ""} onClick={() => setMode("candle")}>Candles</button>
                  <button className={mode === "heikin" ? "on" : ""} onClick={() => setMode("heikin")}>Heikin Ashi</button>
                  <span className="legend"><i className="ema50" /> EMA 50</span>
                  <span className="legend"><i className="ema100" /> EMA 100</span>
                  <span className="legend"><i className="ema200" /> EMA 200</span>
                </div>
              </div>
              <div className="strength">
                <span>Pivot strength</span>
                {STRENGTHS.map((value) => (
                  <button key={value} className={strength === value ? "on" : ""} onClick={() => setStrength(value)}>{value}</button>
                ))}
              </div>
              <OverlayBar overlays={overlays} onChange={setOverlays} />
              {error ? <p className="error">{error}</p> : null}
              {series?.source === "sample" ? <p className="note">กำลังแสดงข้อมูลตัวอย่าง เพราะยังดึง Yahoo Finance ไม่ได้</p> : null}
              <ChartPanel series={series} analysis={analysis} mode={mode} overlays={overlays} loading={loading} />
              {analysis ? <StructureBar analysis={analysis} /> : null}
              {analysis ? <ZoneBoard analysis={analysis} /> : null}
            </div>
            <SummaryPanel summary={analysis?.summary ?? ""} symbol={symbol} loading={loading} />
          </section>
        </main>
      )}
    </div>
  );
}

function OverlayBar({ overlays, onChange }: { overlays: OverlayFlags; onChange: (next: OverlayFlags) => void }) {
  const items: { key: keyof OverlayFlags; label: string }[] = [
    { key: "support", label: "Support" },
    { key: "resistance", label: "Resistance" },
    { key: "orderBlocks", label: "Order Blocks" },
    { key: "fvg", label: "FVG" },
    { key: "liquidity", label: "Liquidity" },
    { key: "poc", label: "POC / HVN / LVN" },
    { key: "ema50", label: "EMA50" },
    { key: "ema100", label: "EMA100" },
    { key: "ema200", label: "EMA200" },
    { key: "bos", label: "BOS" },
    { key: "choch", label: "CHOCH" },
  ];
  return (
    <div className="toggles">
      {items.map((item) => (
        <button
          key={item.key}
          className={overlays[item.key] ? "on" : ""}
          onClick={() => onChange({ ...overlays, [item.key]: !overlays[item.key] })}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

function StructureBar({ analysis }: { analysis: NonNullable<ReturnType<typeof analyzeCached>> }) {
  const lastBos = analysis.bos[analysis.bos.length - 1];
  const lastChoch = analysis.choch[analysis.choch.length - 1];
  const sweep = analysis.liquidity.some((pool) => pool.swept);
  const trendLabel = analysis.trend === "bull" ? "Bull Trend" : analysis.trend === "bear" ? "Bear Trend" : "Range";
  return (
    <div className="structure">
      <span>Trend <b>{trendLabel}</b></span>
      <span>BOS <b>{lastBos ? `${lastBos.direction} ${lastBos.price.toFixed(2)}` : "—"}</b></span>
      <span>CHOCH <b>{lastChoch ? `${lastChoch.direction} ${lastChoch.price.toFixed(2)}` : "—"}</b></span>
      <span>Liquidity <b>{sweep ? "Liquidity Sweep Detected" : "Pools mapped"}</b></span>
    </div>
  );
}

function ZoneBoard({ analysis }: { analysis: NonNullable<ReturnType<typeof analyzeCached>> }) {
  return (
    <div className="zones">
      <div>
        {analysis.supports.map((zone) => <ZoneCard key={zone.id} zone={zone} />)}
      </div>
      <div>
        {analysis.resistances.map((zone) => <ZoneCard key={zone.id} zone={zone} />)}
      </div>
      <article className="summary-card">
        <h3>Technical summary</h3>
        <p>{analysis.summary}</p>
      </article>
    </div>
  );
}

function ZoneCard({ zone }: { zone: NonNullable<ReturnType<typeof analyzeCached>>["zones"][number] }) {
  const title = `${zone.tier === "strong" ? "Strong" : zone.tier === "medium" ? "Medium" : "Weak"} ${zone.kind === "support" ? "Support" : "Resistance"}`;
  return (
    <article className={`zone ${zone.kind}`}>
      <h3>{title}</h3>
      <p className="range">{zone.zoneLow.toFixed(2)} - {zone.zoneHigh.toFixed(2)}</p>
      <p>Strength: <b>{Math.round(zone.score)}%</b></p>
      <p>Touches: <b>{zone.touchCount}</b></p>
      <p>EMA Confluence: <b>{zone.emaConfluence ? "YES" : "NO"}</b></p>
      <p>Multi-Timeframe: <b>{zone.multiTimeframe ? "YES" : "NO"}</b></p>
      <p className="meta">
        {zone.emaLabels.join(", ") || "No EMA"} · {zone.timeframes.join("+")}
        {zone.pocConfluence ? " · POC" : zone.hvnConfluence ? " · HVN" : zone.lvnConfluence ? " · LVN" : ""}
      </p>
    </article>
  );
}

function SummaryPanel({ summary, symbol, loading }: { summary: string; symbol: string; loading: boolean }) {
  return (
    <aside className="chat">
      <header>Market structure summary</header>
      <p className="hint">อ่านโครงสร้างทางเทคนิคของ {symbol} เท่านั้น ไม่ใช่คำแนะนำการลงทุน</p>
      <div className="bubble">{loading ? "กำลังคำนวณโครงสร้างตลาด..." : summary || "ยังไม่มีข้อมูล"}</div>
    </aside>
  );
}

function exportAnalysis(series: QuoteSeries | null, analysis: ReturnType<typeof analyzeCached> | null) {
  const payload = {
    symbol: series?.symbol,
    price: series?.price,
    summary: analysis?.summary,
    zones: analysis?.zones.map((zone) => ({
      kind: zone.kind,
      zoneLow: zone.zoneLow,
      zoneHigh: zone.zoneHigh,
      centerPrice: zone.centerPrice,
      score: zone.score,
      touches: zone.touchCount,
      emaConfluence: zone.emaConfluence,
      multiTimeframe: zone.multiTimeframe,
    })),
    trend: analysis?.trend,
    bos: analysis?.bos,
    choch: analysis?.choch,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${series?.symbol ?? "analysis"}-structure.json`;
  link.click();
  URL.revokeObjectURL(url);
}
