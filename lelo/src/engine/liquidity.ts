import type { Candle, LiquidityPool, Pivot } from "../types";

export function detectLiquidity(
  candles: Candle[],
  pivots: Pivot[],
  atrValue: number,
): LiquidityPool[] {
  const tolerance = Math.max(atrValue * 0.15, 0.01);
  const highs = pivots.filter((pivot) => pivot.type === "high");
  const lows = pivots.filter((pivot) => pivot.type === "low");
  const pools = [
    ...clusterEquals(highs, tolerance, "equal_highs"),
    ...clusterEquals(lows, tolerance, "equal_lows"),
  ];
  for (const pool of pools) {
    const start = Math.max(...pool.indexes) + 1;
    for (let i = start; i < candles.length; i++) {
      const candle = candles[i];
      if (!candle) continue;
      const tookHigh = pool.type === "equal_highs" && candle.high > pool.zoneHigh && candle.close < pool.price;
      const tookLow = pool.type === "equal_lows" && candle.low < pool.zoneLow && candle.close > pool.price;
      if (tookHigh || tookLow) {
        pool.swept = true;
        pool.sweepIndex = i;
        pool.sweepTimestamp = candle.timestamp;
        pool.role = "sweep";
        break;
      }
    }
    if (!pool.swept) pool.role = "stop_hunt";
  }
  return pools.slice(-12);
}

function clusterEquals(
  pivots: Pivot[],
  tolerance: number,
  type: LiquidityPool["type"],
): LiquidityPool[] {
  const sorted = [...pivots].sort((a, b) => a.price - b.price);
  const groups: Pivot[][] = [];
  for (const pivot of sorted) {
    const last = groups[groups.length - 1];
    const anchor = last?.[last.length - 1];
    if (last && anchor && pivot.price - anchor.price <= tolerance) last.push(pivot);
    else groups.push([pivot]);
  }
  return groups
    .filter((group) => group.length >= 2)
    .map((group) => {
      const prices = group.map((pivot) => pivot.price);
      const low = Math.min(...prices);
      const high = Math.max(...prices);
      return {
        id: `${type}-${low.toFixed(4)}-${high.toFixed(4)}`,
        type,
        price: prices.reduce((sum, price) => sum + price, 0) / prices.length,
        zoneLow: low,
        zoneHigh: high,
        timestamps: group.map((pivot) => pivot.timestamp),
        indexes: group.map((pivot) => pivot.index),
        swept: false,
        role: "liquidity_pool" as const,
      };
    });
}
