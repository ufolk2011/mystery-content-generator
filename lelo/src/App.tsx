import { useEffect, useMemo, useState } from "react";
import { Assistant } from "./components/Assistant";
import { BottomDock, type DockTab } from "./components/BottomDock";
import { ChartPanel } from "./components/ChartPanel";
import { WatchlistSidebar } from "./components/WatchlistSidebar";
import { defaultOverlays, type OverlayFlags } from "./chart/overlay";
import { loadSeries, type HistoryRange, type QuoteSeries } from "./data/yahoo";
import { analyzeCached } from "./engine";
import type { PivotStrength } from "./types";

export function App() {
  const [symbol, setSymbol] = useState("META");
  const [query, setQuery] = useState("");
  const [range, setRange] = useState<HistoryRange>("5y");
  const [strength, setStrength] = useState<PivotStrength>(5);
  const [mode, setMode] = useState<"candle" | "heikin">("heikin");
  const [overlays, setOverlays] = useState<OverlayFlags>(defaultOverlays);
  const [series, setSeries] = useState<QuoteSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cash] = useState(20000);
  const [tab, setTab] = useState<DockTab>("zones");
  const [watchOpen, setWatchOpen] = useState(() => window.innerWidth > 1100);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    loadSeries(symbol, range)
      .then((next) => {
        if (!cancelled) setSeries(next);
      })
      .catch((reason: unknown) => {
        if (!cancelled) setError(reason instanceof Error ? reason.message : "Could not load prices");
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
    setQuery("");
  };

  return (
    <div className="app">
      <header className="topbar">
        <button className="menu" onClick={() => setWatchOpen((open) => !open)} aria-label="Toggle watchlist">☰</button>
        <div className="brand">
          <span className="logo">L</span>
          <strong>LELO</strong>
        </div>
        <form
          className="search"
          onSubmit={(event) => {
            event.preventDefault();
            openSymbol(query);
          }}
        >
          <input value={query} placeholder="Search ticker" aria-label="Global ticker search" onChange={(event) => setQuery(event.target.value.toUpperCase())} />
        </form>
        <div className="header-actions">
          <div className="balance">
            <span>Budget</span>
            <strong>{cash.toLocaleString("th-TH", { minimumFractionDigits: 2 })} THB</strong>
          </div>
          <button onClick={() => setTab("portfolio")}>Portfolio</button>
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
        </div>
      </header>
      <div className="terminal">
        <WatchlistSidebar open={watchOpen} active={symbol} onSelect={openSymbol} />
        <div className="stage">
          {error ? <p className="error">{error}</p> : null}
          {series?.source === "sample" ? <p className="note">Showing a sample series because Yahoo Finance did not respond.</p> : null}
          <ChartPanel
            series={series}
            analysis={analysis}
            mode={mode}
            overlays={overlays}
            loading={loading}
            range={range}
            strength={strength}
            onMode={setMode}
            onRange={setRange}
            onStrength={setStrength}
            onOverlays={setOverlays}
          />
          <BottomDock tab={tab} onTab={setTab} symbol={symbol} analysis={analysis} cash={cash} loading={loading} />
        </div>
      </div>
      <Assistant summary={analysis?.summary ?? ""} symbol={symbol} loading={loading} />
    </div>
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
