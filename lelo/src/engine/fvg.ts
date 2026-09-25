import type { Candle, FairValueGap } from "../types";

/**
 * Bullish FVG: candle 1 high is below candle 3 low.
 * Bearish FVG: candle 1 low is above candle 3 high.
 */
export function detectFairValueGaps(candles: Candle[], limit = 12): FairValueGap[] {
  const gaps: FairValueGap[] = [];
  for (let i = 2; i < candles.length; i++) {
    const first = candles[i - 2];
    const third = candles[i];
    if (!first || !third) continue;
    if (first.high < third.low) {
      gaps.push({
        type: "bullish",
        zoneLow: first.high,
        zoneHigh: third.low,
        timestamp: third.timestamp,
        index: i - 1,
        filled: isFilled(candles, i + 1, "bullish", first.high),
      });
    } else if (first.low > third.high) {
      gaps.push({
        type: "bearish",
        zoneLow: third.high,
        zoneHigh: first.low,
        timestamp: third.timestamp,
        index: i - 1,
        filled: isFilled(candles, i + 1, "bearish", first.low),
      });
    }
  }
  return gaps.filter((gap) => !gap.filled).slice(-limit);
}

function isFilled(candles: Candle[], from: number, type: FairValueGap["type"], edge: number): boolean {
  for (let i = from; i < candles.length; i++) {
    const candle = candles[i];
    if (!candle) continue;
    if (type === "bullish" && candle.low <= edge) return true;
    if (type === "bearish" && candle.high >= edge) return true;
  }
  return false;
}
