import type { Analysis, AnalyzeOptions, Candle, PivotStrength, Timeframe, Zone } from "../types";
import { atr, closes, ema, lastFinite, sma, volumes } from "./math";
import { detectOrderBlocks } from "./orderBlocks";
import { detectFairValueGaps } from "./fvg";
import { detectLiquidity } from "./liquidity";
import { detectPivots } from "./pivots";
import { resample } from "./resample";
import { scoreZone, type ScoreContext } from "./scoring";
import { analyzeStructure } from "./structure";
import { buildMarketSummary, rankZones } from "./summary";
import { buildVolumeProfile } from "./volumeProfile";
import { clusterPivots } from "./zones";

const DEFAULT_STRENGTH: PivotStrength = 5;

export function analyzeMarket(candles: Candle[], options: AnalyzeOptions = {}): Analysis {
  const pivotStrength = options.pivotStrength ?? DEFAULT_STRENGTH;
  const includeHigher = options.includeHigherTimeframes !== false;
  const atrSeries = atr(candles, 14);
  const atrValue = Math.max(lastFinite(atrSeries), averageRange(candles));
  const threshold = atrValue * 0.5;
  const pivots = detectPivots(candles, pivotStrength);
  const closeSeries = closes(candles);
  const ema50 = ema(closeSeries, 50);
  const ema100 = ema(closeSeries, 100);
  const ema200 = ema(closeSeries, 200);
  const volumeSma = sma(volumes(candles), 20);
  const profile = buildVolumeProfile(candles);
  const structure = analyzeStructure(candles, pivots);
  const higherZones = includeHigher ? higherTimeframeZones(candles, pivotStrength) : [];

  const context: ScoreContext = {
    candles,
    atr: atrValue,
    volumeSma,
    emas: {
      ema50: finiteAt(ema50),
      ema100: finiteAt(ema100),
      ema200: finiteAt(ema200),
    },
    profile,
    higherZones,
  };

  const rawZones = [
    ...clusterPivots(pivots.filter((pivot) => pivot.type === "low"), threshold, "support"),
    ...clusterPivots(pivots.filter((pivot) => pivot.type === "high"), threshold, "resistance"),
  ];
  const zones = mergeOverlapping(rawZones.map((zone) => scoreZone(zone, context)));
  const price = candles[candles.length - 1]?.close ?? 0;
  const supports = rankZones(zones.filter((zone) => zone.kind === "support"), price, "support");
  const resistances = rankZones(zones.filter((zone) => zone.kind === "resistance"), price, "resistance");
  const liquidity = detectLiquidity(candles, pivots, atrValue);
  const orderBlocks = detectOrderBlocks(candles, structure.bos, atrSeries, volumeSma);
  const fairValueGaps = detectFairValueGaps(candles);

  const analysis: Analysis = {
    pivots,
    zones,
    supports,
    resistances,
    atr: atrValue,
    ema50,
    ema100,
    ema200,
    lastEma: context.emas,
    trend: structure.trend,
    swings: structure.swings,
    bos: structure.bos,
    choch: structure.choch,
    liquidity,
    orderBlocks,
    fairValueGaps,
    profile,
    summary: "",
  };
  analysis.summary = buildMarketSummary({ ...analysis, price });
  return analysis;
}

function higherTimeframeZones(candles: Candle[], strength: PivotStrength) {
  const frames: { unit: "week" | "month"; timeframe: Timeframe }[] = [
    { unit: "week", timeframe: "W" },
    { unit: "month", timeframe: "M" },
  ];
  const zones: ScoreContext["higherZones"] = [];
  for (const frame of frames) {
    const series = resample(candles, frame.unit);
    const frameStrength = fittedStrength(series.length, strength);
    const frameAtr = Math.max(lastFinite(atr(series, 14)), averageRange(series));
    const pivots = detectPivots(series, frameStrength);
    const clustered = [
      ...clusterPivots(pivots.filter((pivot) => pivot.type === "low"), frameAtr * 0.5, "support"),
      ...clusterPivots(pivots.filter((pivot) => pivot.type === "high"), frameAtr * 0.5, "resistance"),
    ];
    for (const zone of clustered) {
      zones.push({
        timeframe: frame.timeframe,
        zoneLow: zone.zoneLow,
        zoneHigh: zone.zoneHigh,
        kind: zone.kind,
      });
    }
  }
  return zones;
}

function fittedStrength(barCount: number, requested: PivotStrength): PivotStrength {
  const allowed: PivotStrength[] = [3, 5, 10, 20];
  const cap = Math.max(3, Math.floor(barCount / 8));
  const fit = allowed.filter((value) => value <= Math.min(requested, cap));
  return fit[fit.length - 1] ?? 3;
}

function finiteAt(values: number[]): number | null {
  const value = lastFinite(values);
  return Number.isFinite(value) && value !== 0 ? value : null;
}

function averageRange(candles: Candle[]): number {
  if (candles.length === 0) return 0;
  const sum = candles.reduce((total, candle) => total + (candle.high - candle.low), 0);
  return sum / candles.length;
}

function clampScore(zone: Zone): number {
  return Math.min(
    100,
    zone.touchScore + zone.rejectionScore + zone.volumeScore + zone.ageScore + zone.timeframeScore + zone.emaScore,
  );
}

function mergeOverlapping(zones: Zone[]): Zone[] {
  const byKind: Zone["kind"][] = ["support", "resistance"];
  const merged: Zone[] = [];
  for (const kind of byKind) {
    const group = zones
      .filter((zone) => zone.kind === kind)
      .sort((a, b) => a.zoneLow - b.zoneLow);
    for (const zone of group) {
      const previous = merged[merged.length - 1];
      if (previous && previous.kind === kind && zone.zoneLow <= previous.zoneHigh) {
        const stronger = zone.score > previous.score ? zone : previous;
        previous.zoneHigh = Math.max(previous.zoneHigh, zone.zoneHigh);
        previous.zoneLow = Math.min(previous.zoneLow, zone.zoneLow);
        previous.centerPrice = (previous.zoneLow + previous.zoneHigh) / 2;
        previous.pivots = [...previous.pivots, ...zone.pivots];
        previous.touchCount = Math.max(previous.touchCount, zone.touchCount);
        previous.touchScore = stronger.touchScore;
        previous.rejectionScore = stronger.rejectionScore;
        previous.maxRejectionPct = stronger.maxRejectionPct;
        previous.volumeScore = stronger.volumeScore;
        previous.ageScore = stronger.ageScore;
        previous.timeframeScore = Math.max(previous.timeframeScore, zone.timeframeScore);
        previous.emaScore = Math.max(previous.emaScore, zone.emaScore);
        previous.score = clampScore(previous);
        previous.tier = previous.score >= 75 ? "strong" : previous.score >= 50 ? "medium" : "weak";
        previous.emaConfluence = previous.emaConfluence || zone.emaConfluence;
        previous.emaLabels = [...new Set([...previous.emaLabels, ...zone.emaLabels])];
        previous.multiTimeframe = previous.multiTimeframe || zone.multiTimeframe;
        previous.timeframes = [...new Set([...previous.timeframes, ...zone.timeframes])];
        previous.pocConfluence = previous.pocConfluence || zone.pocConfluence;
        previous.hvnConfluence = previous.hvnConfluence || zone.hvnConfluence;
        previous.lvnConfluence = previous.lvnConfluence || zone.lvnConfluence;
        previous.id = `${kind}-${previous.zoneLow.toFixed(2)}-${previous.zoneHigh.toFixed(2)}`;
      } else {
        merged.push({ ...zone, pivots: [...zone.pivots], emaLabels: [...zone.emaLabels], timeframes: [...zone.timeframes] });
      }
    }
  }
  return merged;
}

