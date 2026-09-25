import type { Candle, OrderBlock, StructureEvent } from "../types";

export function detectOrderBlocks(
  candles: Candle[],
  bosEvents: StructureEvent[],
  atrValues: number[],
  volumeSma: number[],
  limit = 8,
): OrderBlock[] {
  const blocks: OrderBlock[] = [];
  for (const bos of bosEvents) {
    const atrValue = atrValues[bos.index] ?? 0;
    if (!(atrValue > 0)) continue;
    let origin = -1;
    for (let i = bos.index; i >= Math.max(0, bos.index - 12); i--) {
      const candle = candles[i];
      if (!candle) continue;
      const bearish = candle.close < candle.open;
      const bullish = candle.close > candle.open;
      if (bos.direction === "bullish" && bearish) {
        origin = i;
        break;
      }
      if (bos.direction === "bearish" && bullish) {
        origin = i;
        break;
      }
    }
    if (origin < 0) continue;
    const candle = candles[origin];
    const breakCandle = candles[bos.index];
    if (!candle || !breakCandle) continue;
    const impulse =
      bos.direction === "bullish" ? breakCandle.close - candle.low : candle.high - breakCandle.close;
    if (impulse < atrValue) continue;

    let maxVolumeRatio = 0;
    for (let i = origin; i <= bos.index; i++) {
      const sma = volumeSma[i] ?? 0;
      const bar = candles[i];
      if (sma > 0 && bar) maxVolumeRatio = Math.max(maxVolumeRatio, bar.volume / sma);
    }
    if (maxVolumeRatio < 1.05 && impulse < atrValue * 1.8) continue;

    const low = Math.min(candle.low, candle.high);
    const high = Math.max(candle.low, candle.high);
    const mitigated = isMitigated(candles, origin + 1, bos.direction, low, high);
    const strength = Math.round(
      Math.min(100, (impulse / atrValue) * 18 + Math.min(maxVolumeRatio, 3) * 16),
    );
    blocks.push({
      type: bos.direction,
      priceRange: { low, high },
      timestamp: candle.timestamp,
      index: origin,
      strength,
      mitigated,
    });
  }
  const active = blocks.filter((block) => !block.mitigated);
  return (active.length > 0 ? active : blocks).slice(-limit);
}

function isMitigated(
  candles: Candle[],
  from: number,
  direction: StructureEvent["direction"],
  low: number,
  high: number,
): boolean {
  for (let i = from; i < candles.length; i++) {
    const candle = candles[i];
    if (!candle) continue;
    if (direction === "bullish" && candle.close < low) return true;
    if (direction === "bearish" && candle.close > high) return true;
  }
  return false;
}
