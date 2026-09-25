import type { Candle } from "../types";

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

export function sma(values: number[], period: number): number[] {
  const out = new Array<number>(values.length).fill(Number.NaN);
  if (period <= 0) return out;
  let sum = 0;
  for (let i = 0; i < values.length; i++) {
    sum += values[i] ?? 0;
    if (i >= period) sum -= values[i - period] ?? 0;
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

export function ema(values: number[], period: number): number[] {
  const out = new Array<number>(values.length).fill(Number.NaN);
  if (period <= 0 || values.length === 0) return out;
  const k = 2 / (period + 1);
  let sum = 0;
  let prev = 0;
  for (let i = 0; i < values.length; i++) {
    const value = values[i] ?? 0;
    if (i < period) {
      sum += value;
      if (i === period - 1) {
        prev = sum / period;
        out[i] = prev;
      }
      continue;
    }
    prev = value * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

export function trueRanges(candles: Candle[]): number[] {
  return candles.map((candle, index) => {
    if (index === 0) return candle.high - candle.low;
    const prevClose = candles[index - 1]?.close ?? candle.close;
    return Math.max(
      candle.high - candle.low,
      Math.abs(candle.high - prevClose),
      Math.abs(candle.low - prevClose),
    );
  });
}

/** Wilder ATR. Index 0..period-2 stay NaN. */
export function atr(candles: Candle[], period = 14): number[] {
  const tr = trueRanges(candles);
  const out = new Array<number>(candles.length).fill(Number.NaN);
  if (period <= 0) return out;
  let seed = 0;
  for (let i = 0; i < tr.length; i++) {
    const value = tr[i] ?? 0;
    if (i < period) {
      seed += value;
      if (i === period - 1) out[i] = seed / period;
      continue;
    }
    const prev = out[i - 1] ?? seed / period;
    out[i] = (prev * (period - 1) + value) / period;
  }
  return out;
}

export function lastFinite(values: number[]): number {
  for (let i = values.length - 1; i >= 0; i--) {
    const value = values[i];
    if (value != null && Number.isFinite(value)) return value;
  }
  return 0;
}

export function closes(candles: Candle[]): number[] {
  return candles.map((candle) => candle.close);
}

export function volumes(candles: Candle[]): number[] {
  return candles.map((candle) => candle.volume);
}
