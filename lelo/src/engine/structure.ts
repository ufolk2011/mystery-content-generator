import type { Candle, Direction, Pivot, StructureEvent, SwingLabel, Trend } from "../types";

export interface StructureResult {
  trend: Trend;
  swings: SwingLabel[];
  bos: StructureEvent[];
  choch: StructureEvent[];
}

export function analyzeStructure(candles: Candle[], pivots: Pivot[]): StructureResult {
  const ordered = [...pivots].sort((a, b) => a.index - b.index || (a.type === "low" ? -1 : 1));
  const events: StructureEvent[] = [];
  const swings: SwingLabel[] = [];
  let bias: Trend = "range";
  let lastHigh: Pivot | null = null;
  let lastLow: Pivot | null = null;
  const brokenHighs = new Set<number>();
  const brokenLows = new Set<number>();

  const pushBreak = (direction: Direction, level: Pivot, from: number, to: number) => {
    const index = findBreak(candles, direction, level.price, from, to);
    if (index == null) return;
    const against =
      (direction === "bullish" && bias === "bear") || (direction === "bearish" && bias === "bull");
    const candle = candles[index];
    if (!candle) return;
    events.push({
      kind: against ? "choch" : "bos",
      direction,
      price: level.price,
      timestamp: candle.timestamp,
      index,
    });
    bias = direction === "bullish" ? "bull" : "bear";
  };

  for (const pivot of ordered) {
    if (pivot.type === "high") {
      if (lastHigh) {
        swings.push({
          type: "high",
          label: pivot.price > lastHigh.price ? "HH" : pivot.price < lastHigh.price ? "LH" : "EH",
          price: pivot.price,
          timestamp: pivot.timestamp,
          index: pivot.index,
        });
        if (pivot.price > lastHigh.price && !brokenHighs.has(lastHigh.index)) {
          pushBreak("bullish", lastHigh, lastHigh.index + 1, pivot.index);
          brokenHighs.add(lastHigh.index);
        }
      } else {
        swings.push({
          type: "high",
          label: "HH",
          price: pivot.price,
          timestamp: pivot.timestamp,
          index: pivot.index,
        });
      }
      lastHigh = pivot;
    } else if (lastLow) {
      swings.push({
        type: "low",
        label: pivot.price > lastLow.price ? "HL" : pivot.price < lastLow.price ? "LL" : "EL",
        price: pivot.price,
        timestamp: pivot.timestamp,
        index: pivot.index,
      });
      if (pivot.price < lastLow.price && !brokenLows.has(lastLow.index)) {
        pushBreak("bearish", lastLow, lastLow.index + 1, pivot.index);
        brokenLows.add(lastLow.index);
      }
      lastLow = pivot;
    } else {
      swings.push({
        type: "low",
        label: "LL",
        price: pivot.price,
        timestamp: pivot.timestamp,
        index: pivot.index,
      });
      lastLow = pivot;
    }
  }

  const lastIndex = candles.length - 1;
  const lastCandle = candles[lastIndex];
  if (lastCandle && lastHigh && lastCandle.close > lastHigh.price && !brokenHighs.has(lastHigh.index)) {
    pushBreak("bullish", lastHigh, lastHigh.index + 1, lastIndex);
  }
  if (lastCandle && lastLow && lastCandle.close < lastLow.price && !brokenLows.has(lastLow.index)) {
    pushBreak("bearish", lastLow, lastLow.index + 1, lastIndex);
  }

  return {
    trend: deriveTrend(swings, bias),
    swings,
    bos: events.filter((event) => event.kind === "bos"),
    choch: events.filter((event) => event.kind === "choch"),
  };
}

function findBreak(
  candles: Candle[],
  direction: Direction,
  level: number,
  from: number,
  to: number,
): number | null {
  const end = Math.min(candles.length - 1, to);
  for (let i = Math.max(0, from); i <= end; i++) {
    const candle = candles[i];
    if (!candle) continue;
    if (direction === "bullish" && candle.close > level) return i;
    if (direction === "bearish" && candle.close < level) return i;
  }
  return null;
}

function deriveTrend(swings: SwingLabel[], bias: Trend): Trend {
  const lastHigh = [...swings].reverse().find((swing) => swing.type === "high");
  const lastLow = [...swings].reverse().find((swing) => swing.type === "low");
  if (lastHigh?.label === "HH" && (lastLow?.label === "HL" || lastLow?.label === "LL" && bias === "bull")) {
    if (lastLow.label === "HL") return "bull";
  }
  if (lastHigh?.label === "HH" && lastLow?.label === "HL") return "bull";
  if (lastHigh?.label === "LH" && lastLow?.label === "LL") return "bear";
  if (bias === "bull" || bias === "bear") return bias;
  return "range";
}
