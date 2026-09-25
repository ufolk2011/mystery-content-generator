import type { Candle } from "../types";

function bucketStart(timestamp: number, unit: "week" | "month"): number {
  const date = new Date(timestamp);
  if (unit === "month") {
    return Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1);
  }
  const day = date.getUTCDay();
  const mondayOffset = day === 0 ? 6 : day - 1;
  const start = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate());
  return start - mondayOffset * 86_400_000;
}

export function resample(candles: Candle[], unit: "week" | "month"): Candle[] {
  const groups = new Map<number, Candle>();
  for (const candle of candles) {
    const key = bucketStart(candle.timestamp, unit);
    const existing = groups.get(key);
    if (!existing) {
      groups.set(key, { ...candle, timestamp: key });
      continue;
    }
    existing.high = Math.max(existing.high, candle.high);
    existing.low = Math.min(existing.low, candle.low);
    existing.close = candle.close;
    existing.volume += candle.volume;
  }
  return [...groups.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([, candle]) => candle);
}

export function heikinAshi(candles: Candle[]): Candle[] {
  const out: Candle[] = [];
  for (let i = 0; i < candles.length; i++) {
    const candle = candles[i];
    if (!candle) continue;
    const close = (candle.open + candle.high + candle.low + candle.close) / 4;
    const prev = out[i - 1];
    const open = prev ? (prev.open + prev.close) / 2 : (candle.open + candle.close) / 2;
    out.push({
      timestamp: candle.timestamp,
      open,
      close,
      high: Math.max(candle.high, open, close),
      low: Math.min(candle.low, open, close),
      volume: candle.volume,
    });
  }
  return out;
}
