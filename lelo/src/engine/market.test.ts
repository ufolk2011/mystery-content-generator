import { describe, expect, it } from "vitest";
import type { Candle, PivotStrength } from "../types";
import { analyzeCached, clearAnalysisCache } from "./cache";
import { analyzeMarket } from "./analyze";
import { detectFairValueGaps } from "./fvg";
import { detectPivots } from "./pivots";
import { clusterPivots } from "./zones";
import { buildVolumeProfile } from "./volumeProfile";

function candle(index: number, high: number, low: number, close = (high + low) / 2, volume = 1000): Candle {
  return {
    timestamp: Date.UTC(2020, 0, 1) + index * 86_400_000,
    open: close,
    high,
    low,
    close,
    volume,
  };
}

describe("pivot detection", () => {
  it("marks a strict pivot high and pivot low", () => {
    const highs = [1, 2, 3, 4, 8, 4, 3, 2, 1];
    const lows = [0, 1, 2, 3, 4, 3, 2, 1, 0];
    const candles = highs.map((high, index) => candle(index, high, lows[index] ?? 0));
    const pivots = detectPivots(candles, 3);
    expect(pivots.find((pivot) => pivot.type === "high")?.price).toBe(8);
    expect(pivots.find((pivot) => pivot.type === "low")).toBeUndefined();
  });

  it("requires both sides for the configured strength", () => {
    const candles = Array.from({ length: 11 }, (_, index) => candle(index, index === 5 ? 10 : 4, index === 5 ? 3 : 1));
    expect(detectPivots(candles, 5).some((pivot) => pivot.type === "high" && pivot.price === 10)).toBe(true);
    expect(detectPivots(candles, 10)).toHaveLength(0);
  });
});

describe("zone clustering", () => {
  it("merges nearby pivot prices into one zone", () => {
    const pivots = [742, 744, 747].map((price, index) => ({
      price,
      timestamp: index,
      index,
      type: "low" as const,
      strength: 5 as PivotStrength,
      volume: 100,
    }));
    const [zone] = clusterPivots(pivots, 6, "support");
    expect(zone?.zoneLow).toBeLessThanOrEqual(742);
    expect(zone?.zoneHigh).toBeGreaterThanOrEqual(747);
    expect(zone?.pivots).toHaveLength(3);
  });

  it("keeps distant pivots in separate zones", () => {
    const pivots = [700, 800].map((price, index) => ({
      price,
      timestamp: index,
      index,
      type: "high" as const,
      strength: 5 as PivotStrength,
      volume: 100,
    }));
    expect(clusterPivots(pivots, 5, "resistance")).toHaveLength(2);
  });
});

describe("fair value gaps", () => {
  it("stores a bullish gap when candle 1 high is below candle 3 low", () => {
    const candles = [
      candle(0, 10, 8, 9),
      candle(1, 14, 11, 13),
      candle(2, 16, 12, 15),
    ];
    const gaps = detectFairValueGaps(candles);
    expect(gaps[0]?.type).toBe("bullish");
    expect(gaps[0]?.zoneLow).toBe(10);
    expect(gaps[0]?.zoneHigh).toBe(12);
  });
});

describe("volume profile", () => {
  it("places the point of control on the heaviest price bin", () => {
    const candles = [
      ...Array.from({ length: 20 }, (_, index) => candle(index, 101, 99, 100, 500)),
      ...Array.from({ length: 5 }, (_, index) => candle(20 + index, 121, 119, 120, 50)),
    ];
    const profile = buildVolumeProfile(candles);
    expect(profile.poc).not.toBeNull();
    expect(profile.poc?.price ?? 0).toBeGreaterThan(98);
    expect(profile.poc?.price ?? 0).toBeLessThan(104);
  });
});

describe("market analysis", () => {
  it("scores zones from 0 to 100 and classifies trend", () => {
    const candles = trendingCandles(180);
    const analysis = analyzeMarket(candles, { pivotStrength: 3 });
    expect(analysis.pivots.length).toBeGreaterThan(0);
    expect(analysis.zones.length).toBeGreaterThan(0);
    for (const zone of analysis.zones) {
      expect(zone.score).toBeGreaterThanOrEqual(0);
      expect(zone.score).toBeLessThanOrEqual(100);
      expect(zone.zoneLow).toBeLessThanOrEqual(zone.zoneHigh);
      expect(zone.touchScore + zone.rejectionScore + zone.volumeScore + zone.ageScore + zone.timeframeScore + zone.emaScore).toBeCloseTo(
        zone.score,
        5,
      );
    }
    expect(["bull", "bear", "range"]).toContain(analysis.trend);
    expect(analysis.summary).toMatch(/not financial advice/i);
    expect(analysis.summary.toLowerCase()).not.toMatch(/buy|sell|เข้าซื้อ/);
  });

  it("returns the cached analysis for the same series", () => {
    clearAnalysisCache();
    const candles = trendingCandles(80);
    const first = analyzeCached(candles, "TEST", { pivotStrength: 5 });
    const second = analyzeCached(candles, "TEST", { pivotStrength: 5 });
    expect(second).toBe(first);
  });

  it("finishes 5000 candles without a multi-second stall", () => {
    const candles = trendingCandles(5000);
    const started = performance.now();
    const analysis = analyzeMarket(candles, { pivotStrength: 5 });
    const elapsed = performance.now() - started;
    expect(analysis.zones.length).toBeGreaterThan(0);
    expect(elapsed).toBeLessThan(1500);
  });
});

function trendingCandles(count: number): Candle[] {
  const candles: Candle[] = [];
  let price = 100;
  for (let i = 0; i < count; i++) {
    const wave = Math.sin(i / 9) * 4;
    const drift = i * 0.08;
    const close = 100 + drift + wave;
    const high = Math.max(price, close) + 1.2 + (i % 17 === 0 ? 3 : 0);
    const low = Math.min(price, close) - 1.1;
    const volume = 1000 + (i % 23 === 0 ? 8000 : (i % 7) * 80);
    candles.push({
      timestamp: Date.UTC(2010, 0, 1) + i * 86_400_000,
      open: price,
      high,
      low,
      close,
      volume,
    });
    price = close;
    if (i % 40 === 0 && i > 10) {
      const gap = candles[i];
      if (gap) {
        gap.low = gap.close + 2;
        gap.high = gap.low + 2;
        gap.open = gap.low + 0.4;
      }
    }
  }
  return candles;
}
