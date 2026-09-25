import type { Candle } from "../types";

export interface QuoteSeries {
  symbol: string;
  name: string;
  currency: string;
  price: number;
  change: number;
  changePercent: number;
  candles: Candle[];
  source: "yahoo" | "sample";
}

const RANGES = ["1y", "2y", "5y", "10y"] as const;
export type HistoryRange = (typeof RANGES)[number];

export async function loadSeries(symbol: string, range: HistoryRange): Promise<QuoteSeries> {
  const clean = symbol.trim().toUpperCase();
  try {
    return await fetchYahoo(clean, range);
  } catch (error) {
    console.warn("Yahoo Finance unavailable, using sample series", error);
    return sampleSeries(clean);
  }
}

async function fetchYahoo(symbol: string, range: HistoryRange): Promise<QuoteSeries> {
  const response = await fetch(`/api/yahoo/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=${range}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new Error(`Yahoo ${response.status}`);
  const payload = (await response.json()) as YahooChart;
  const result = payload.chart?.result?.[0];
  const quote = result?.indicators?.quote?.[0];
  const timestamps = result?.timestamp ?? [];
  if (!result || !quote || timestamps.length === 0) throw new Error("Empty Yahoo payload");

  const candles: Candle[] = [];
  for (let i = 0; i < timestamps.length; i++) {
    const open = quote.open?.[i];
    const high = quote.high?.[i];
    const low = quote.low?.[i];
    const close = quote.close?.[i];
    const volume = quote.volume?.[i];
    const timestamp = timestamps[i];
    if (
      timestamp == null ||
      open == null ||
      high == null ||
      low == null ||
      close == null ||
      volume == null
    ) {
      continue;
    }
    candles.push({ timestamp: timestamp * 1000, open, high, low, close, volume });
  }
  if (candles.length < 30) throw new Error("Not enough candles");
  const meta = result.meta;
  const price = meta?.regularMarketPrice ?? candles[candles.length - 1]?.close ?? 0;
  const previous = candles[candles.length - 2]?.close ?? price;
  const change = price - previous;
  return {
    symbol,
    name: meta?.shortName || meta?.longName || symbol,
    currency: meta?.currency || "USD",
    price,
    change,
    changePercent: previous ? (change / previous) * 100 : 0,
    candles,
    source: "yahoo",
  };
}

interface YahooChart {
  chart?: {
    result?: {
      timestamp?: number[];
      meta?: {
        shortName?: string;
        longName?: string;
        currency?: string;
        regularMarketPrice?: number;
      };
      indicators?: {
        quote?: {
          open?: (number | null)[];
          high?: (number | null)[];
          low?: (number | null)[];
          close?: (number | null)[];
          volume?: (number | null)[];
        }[];
      };
    }[];
  };
}

function sampleSeries(symbol: string): QuoteSeries {
  const candles: Candle[] = [];
  let price = 180;
  for (let i = 0; i < 700; i++) {
    const wave = Math.sin(i / 18) * 12 + Math.sin(i / 6) * 4;
    const close = 180 + i * 0.35 + wave;
    const open = price;
    const high = Math.max(open, close) + 2 + (i % 29 === 0 ? 6 : 0);
    const low = Math.min(open, close) - 2.2;
    candles.push({
      timestamp: Date.UTC(2023, 0, 2) + i * 86_400_000,
      open,
      high,
      low,
      close,
      volume: 1_200_000 + (i % 21 === 0 ? 6_000_000 : (i % 5) * 80_000),
    });
    price = close;
  }
  const last = candles[candles.length - 1]?.close ?? price;
  const prev = candles[candles.length - 2]?.close ?? last;
  return {
    symbol,
    name: `${symbol} sample`,
    currency: "USD",
    price: last,
    change: last - prev,
    changePercent: prev ? ((last - prev) / prev) * 100 : 0,
    candles,
    source: "sample",
  };
}

export interface TickQuote {
  price: number;
  changePercent: number;
}

export async function loadQuotes(symbols: string[]): Promise<Record<string, TickQuote>> {
  const pairs = await Promise.all(
    symbols.map(async (symbol) => {
      try {
        const response = await fetch(`/api/yahoo/v8/finance/chart/${encodeURIComponent(symbol)}?interval=1d&range=5d`);
        if (!response.ok) return [symbol, { price: 0, changePercent: 0 }] as const;
        const payload = (await response.json()) as YahooChart;
        const closes = payload.chart?.result?.[0]?.indicators?.quote?.[0]?.close?.filter((value): value is number => value != null) ?? [];
        const price = closes[closes.length - 1] ?? 0;
        const previous = closes[closes.length - 2] ?? price;
        return [symbol, { price, changePercent: previous ? ((price - previous) / previous) * 100 : 0 }] as const;
      } catch {
        return [symbol, { price: 0, changePercent: 0 }] as const;
      }
    }),
  );
  return Object.fromEntries(pairs);
}

export interface NewsItem {
  title: string;
  link: string;
  publisher: string;
}

export async function loadNews(symbol: string): Promise<NewsItem[]> {
  const response = await fetch(`/api/yahoo/v1/finance/search?q=${encodeURIComponent(symbol)}&newsCount=8&quotesCount=0`);
  if (!response.ok) return [];
  const payload = (await response.json()) as { news?: { title?: string; link?: string; publisher?: string }[] };
  return (payload.news ?? [])
    .filter((item) => item.title && item.link)
    .map((item) => ({ title: item.title as string, link: item.link as string, publisher: item.publisher || "Yahoo Finance" }));
}
