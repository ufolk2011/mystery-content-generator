import type { Candle, Pivot, PivotStrength } from "../types";

/**
 * A pivot high is strictly greater than `strength` candles on both sides.
 * A pivot low is strictly lower than `strength` candles on both sides.
 */
export function detectPivots(candles: Candle[], strength: PivotStrength): Pivot[] {
  const pivots: Pivot[] = [];
  const n = candles.length;
  if (strength < 1 || n < strength * 2 + 1) return pivots;

  for (let i = strength; i < n - strength; i++) {
    const candle = candles[i];
    if (!candle) continue;
    let isHigh = true;
    let isLow = true;
    for (let j = 1; j <= strength; j++) {
      const left = candles[i - j];
      const right = candles[i + j];
      if (!left || !right) {
        isHigh = false;
        isLow = false;
        break;
      }
      if (left.high >= candle.high || right.high >= candle.high) isHigh = false;
      if (left.low <= candle.low || right.low <= candle.low) isLow = false;
      if (!isHigh && !isLow) break;
    }
    if (isHigh) {
      pivots.push({
        price: candle.high,
        timestamp: candle.timestamp,
        index: i,
        type: "high",
        strength,
        volume: candle.volume,
      });
    }
    if (isLow) {
      pivots.push({
        price: candle.low,
        timestamp: candle.timestamp,
        index: i,
        type: "low",
        strength,
        volume: candle.volume,
      });
    }
  }
  return pivots;
}
