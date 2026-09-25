import { useEffect, useState } from "react";
import { loadNews, type NewsItem } from "../data/yahoo";
import type { Analysis } from "../types";

export type DockTab = "journal" | "zones" | "summary" | "news" | "portfolio";

interface JournalEntry {
  id: string;
  symbol: string;
  note: string;
  createdAt: number;
}

interface Props {
  tab: DockTab;
  onTab: (tab: DockTab) => void;
  symbol: string;
  analysis: Analysis | null;
  cash: number;
  loading: boolean;
}

export function BottomDock({ tab, onTab, symbol, analysis, cash, loading }: Props) {
  const tabs: { id: DockTab; label: string }[] = [
    { id: "journal", label: "Trade Journal" },
    { id: "zones", label: "Support & Resistance" },
    { id: "summary", label: "AI Summary" },
    { id: "news", label: "News" },
    { id: "portfolio", label: "Portfolio" },
  ];
  return (
    <section className="dock">
      <div className="dock-tabs">
        {tabs.map((item) => (
          <button key={item.id} className={tab === item.id ? "on" : ""} onClick={() => onTab(item.id)}>
            {item.label}
          </button>
        ))}
      </div>
      <div className="dock-body">
        {tab === "journal" ? <Journal symbol={symbol} /> : null}
        {tab === "zones" && analysis ? <ZoneList analysis={analysis} /> : null}
        {tab === "summary" ? <p className="summary-copy">{loading ? "Calculating structure..." : analysis?.summary || "No summary yet."}</p> : null}
        {tab === "news" ? <NewsList symbol={symbol} /> : null}
        {tab === "portfolio" ? <Portfolio cash={cash} symbol={symbol} /> : null}
      </div>
    </section>
  );
}

function ZoneList({ analysis }: { analysis: Analysis }) {
  const zones = [...analysis.supports, ...analysis.resistances];
  return (
    <div className="zone-row">
      {zones.map((zone) => (
        <article key={zone.id} className={`zone ${zone.kind}`}>
          <h3>{zone.tier === "strong" ? "Strong" : zone.tier === "medium" ? "Medium" : "Weak"} {zone.kind === "support" ? "Support" : "Resistance"}</h3>
          <p className="range">{zone.zoneLow.toFixed(2)} - {zone.zoneHigh.toFixed(2)}</p>
          <p>Strength: <b>{Math.round(zone.score)}%</b></p>
          <p>Touches: <b>{zone.touchCount}</b></p>
          <p>EMA Confluence: <b>{zone.emaConfluence ? "YES" : "NO"}</b></p>
          <p>Multi-Timeframe: <b>{zone.multiTimeframe ? "YES" : "NO"}</b></p>
        </article>
      ))}
      <article className="zone structure-note">
        <h3>{analysis.trend === "bull" ? "Bull Trend" : analysis.trend === "bear" ? "Bear Trend" : "Range"}</h3>
        <p>BOS: {analysis.bos.at(-1) ? `${analysis.bos.at(-1)?.direction} ${analysis.bos.at(-1)?.price.toFixed(2)}` : "—"}</p>
        <p>CHOCH: {analysis.choch.at(-1) ? `${analysis.choch.at(-1)?.direction} ${analysis.choch.at(-1)?.price.toFixed(2)}` : "—"}</p>
        <p>{analysis.liquidity.some((pool) => pool.swept) ? "Liquidity Sweep Detected" : "Liquidity pools mapped"}</p>
      </article>
    </div>
  );
}

function Journal({ symbol }: { symbol: string }) {
  const [entries, setEntries] = useState<JournalEntry[]>(() => readJournal());
  const [note, setNote] = useState("");
  useEffect(() => {
    localStorage.setItem("lelo.journal", JSON.stringify(entries));
  }, [entries]);
  return (
    <div className="journal">
      <form
        onSubmit={(event) => {
          event.preventDefault();
          if (!note.trim()) return;
          setEntries((current) => [{ id: crypto.randomUUID(), symbol, note: note.trim(), createdAt: Date.now() }, ...current]);
          setNote("");
        }}
      >
        <input value={note} onChange={(event) => setNote(event.target.value)} placeholder={`Journal note for ${symbol}`} />
        <button>Save</button>
      </form>
      <ul>
        {entries.map((entry) => (
          <li key={entry.id}>
            <b>{entry.symbol}</b> {entry.note}
            <button onClick={() => setEntries((current) => current.filter((item) => item.id !== entry.id))}>Remove</button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function NewsList({ symbol }: { symbol: string }) {
  const [items, setItems] = useState<NewsItem[]>([]);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    void loadNews(symbol)
      .then((next) => {
        if (!cancelled) setItems(next);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [symbol]);
  if (failed || items.length === 0) {
    return (
      <p>
        Headlines are unavailable.{" "}
        <a href={`https://finance.yahoo.com/quote/${symbol}/news`} target="_blank" rel="noreferrer">
          Open {symbol} news
        </a>
      </p>
    );
  }
  return (
    <ul className="news-list">
      {items.map((item) => (
        <li key={item.link}>
          <a href={item.link} target="_blank" rel="noreferrer">{item.title}</a>
          <small>{item.publisher}</small>
        </li>
      ))}
    </ul>
  );
}

function Portfolio({ cash, symbol }: { cash: number; symbol: string }) {
  const [shares, setShares] = useState(() => localStorage.getItem("lelo.shares") || "");
  return (
    <div>
      <p>Cash balance: <b>{cash.toLocaleString("th-TH", { minimumFractionDigits: 2 })} THB</b></p>
      <p>Local portfolio only. This is not a brokerage account and not financial advice.</p>
      <label>
        {symbol} shares
        <input
          value={shares}
          onChange={(event) => {
            setShares(event.target.value);
            localStorage.setItem("lelo.shares", event.target.value);
          }}
        />
      </label>
    </div>
  );
}

function readJournal(): JournalEntry[] {
  try {
    const raw = localStorage.getItem("lelo.journal");
    const parsed = raw ? (JSON.parse(raw) as JournalEntry[]) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}
