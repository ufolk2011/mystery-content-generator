import type { Analysis, AnalyzeOptions, Candle } from "../types";
import { analyzeMarket } from "./analyze";

const cache = new Map<string, Analysis>();
const MAX_ENTRIES = 8;

export function analyzeCached(candles: Candle[], symbol: string, options: AnalyzeOptions = {}): Analysis {
  const last = candles[candles.length - 1];
  const key = [
    symbol,
    options.pivotStrength ?? 5,
    options.includeHigherTimeframes === false ? "base" : "mtf",
    candles.length,
    last?.timestamp ?? 0,
    last?.close ?? 0,
  ].join("|");
  const hit = cache.get(key);
  if (hit) return hit;
  const analysis = analyzeMarket(candles, options);
  cache.set(key, analysis);
  if (cache.size > MAX_ENTRIES) {
    const oldest = cache.keys().next().value;
    if (oldest) cache.delete(oldest);
  }
  return analysis;
}

export function clearAnalysisCache(): void {
  cache.clear();
}
