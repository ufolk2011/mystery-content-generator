import { useEffect, useState } from "react";
import { loadQuotes, type TickQuote } from "../data/yahoo";

export interface WatchItem {
  symbol: string;
  favorite: boolean;
  pinned: boolean;
}

const DEFAULT_ITEMS: WatchItem[] = ["PLTR", "MU", "ZS", "TEM", "FPS", "META", "RKLB", "GOOG", "ISRG", "NEE", "UNH", "STIM"].map(
  (symbol) => ({
    symbol,
    favorite: ["META", "TEM", "PLTR"].includes(symbol),
    pinned: ["META", "TEM", "PLTR"].includes(symbol),
  }),
);

interface Props {
  open: boolean;
  active: string;
  onSelect: (symbol: string) => void;
}

export function WatchlistSidebar({ open, active, onSelect }: Props) {
  const [items, setItems] = useState<WatchItem[]>(() => readItems());
  const [quotes, setQuotes] = useState<Record<string, TickQuote>>({});
  const [query, setQuery] = useState("");
  const [dragIndex, setDragIndex] = useState<number | null>(null);

  useEffect(() => {
    localStorage.setItem("lelo.watchlist", JSON.stringify(items));
  }, [items]);

  useEffect(() => {
    let cancelled = false;
    void loadQuotes(items.map((item) => item.symbol)).then((next) => {
      if (!cancelled) setQuotes(next);
    });
    return () => {
      cancelled = true;
    };
  }, [items]);

  const shown = items
    .map((item, index) => ({ item, index }))
    .filter(({ item }) => item.symbol.includes(query.trim().toUpperCase()));
  const featured = shown.filter(({ item }) => item.pinned || item.favorite);
  const rest = shown.filter(({ item }) => !item.pinned && !item.favorite);

  const add = () => {
    const symbol = query.trim().toUpperCase();
    if (!symbol || items.some((item) => item.symbol === symbol)) {
      if (symbol) onSelect(symbol);
      return;
    }
    setItems((current) => [...current, { symbol, favorite: false, pinned: false }]);
    onSelect(symbol);
    setQuery("");
  };

  const move = (from: number, to: number) => {
    if (to < 0 || to >= items.length || from === to) return;
    setItems((current) => {
      const next = [...current];
      const [item] = next.splice(from, 1);
      if (!item) return current;
      next.splice(to, 0, item);
      return next;
    });
  };

  return (
    <aside className={`watch-side ${open ? "open" : ""}`}>
      <div className="watch-search">
        <input
          value={query}
          placeholder="Search or add ticker"
          aria-label="Search watchlist"
          onChange={(event) => setQuery(event.target.value.toUpperCase())}
          onKeyDown={(event) => {
            if (event.key === "Enter") add();
          }}
        />
        <button onClick={add}>Add</button>
      </div>
      <ul>
        {featured.map(({ item, index }) => (
          <Row
            key={item.symbol}
            item={item}
            quote={quotes[item.symbol]}
            active={item.symbol === active}
            onSelect={onSelect}
            onChange={(next) => setItems((current) => current.map((row) => (row.symbol === next.symbol ? next : row)))}
            onRemove={() => setItems((current) => current.filter((row) => row.symbol !== item.symbol))}
            onDragStart={() => setDragIndex(index)}
            onDrop={() => {
              if (dragIndex != null) move(dragIndex, index);
              setDragIndex(null);
            }}
          />
        ))}
      </ul>
      <div className="watch-split" />
      <ul>
        {rest.map(({ item, index }) => (
          <Row
            key={item.symbol}
            item={item}
            quote={quotes[item.symbol]}
            active={item.symbol === active}
            onSelect={onSelect}
            onChange={(next) => setItems((current) => current.map((row) => (row.symbol === next.symbol ? next : row)))}
            onRemove={() => setItems((current) => current.filter((row) => row.symbol !== item.symbol))}
            onDragStart={() => setDragIndex(index)}
            onDrop={() => {
              if (dragIndex != null) move(dragIndex, index);
              setDragIndex(null);
            }}
          />
        ))}
      </ul>
    </aside>
  );
}

function Row({
  item,
  quote,
  active,
  onSelect,
  onChange,
  onRemove,
  onDragStart,
  onDrop,
}: {
  item: WatchItem;
  quote?: TickQuote;
  active: boolean;
  onSelect: (symbol: string) => void;
  onChange: (item: WatchItem) => void;
  onRemove: () => void;
  onDragStart: () => void;
  onDrop: () => void;
}) {
  const up = (quote?.changePercent ?? 0) >= 0;
  return (
    <li
      className={active ? "active" : ""}
      draggable
      onDragStart={onDragStart}
      onDragOver={(event) => event.preventDefault()}
      onDrop={onDrop}
    >
      <button className="watch-main" onClick={() => onSelect(item.symbol)}>
        <b>{item.favorite ? "★ " : ""}{item.symbol}</b>
        <small>{quote && quote.price ? `$${quote.price.toFixed(2)}` : "—"}</small>
        <em className={up ? "up" : "down"}>{quote && quote.price ? `${up ? "+" : ""}${quote.changePercent.toFixed(2)}%` : ""}</em>
      </button>
      <button title="Favorite" onClick={() => onChange({ ...item, favorite: !item.favorite })}>{item.favorite ? "★" : "☆"}</button>
      <button title="Pin" onClick={() => onChange({ ...item, pinned: !item.pinned })}>{item.pinned ? "📌" : "Pin"}</button>
      <button title="Remove" onClick={onRemove}>×</button>
    </li>
  );
}

function readItems(): WatchItem[] {
  try {
    const raw = localStorage.getItem("lelo.watchlist");
    if (!raw) return DEFAULT_ITEMS;
    const parsed = JSON.parse(raw) as WatchItem[];
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : DEFAULT_ITEMS;
  } catch {
    return DEFAULT_ITEMS;
  }
}
