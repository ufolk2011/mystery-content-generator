import { clamp } from "./math";
import { profileConfluence } from "./volumeProfile";
import type { Candle, Pivot, Timeframe, VolumeProfile, Zone, ZoneTier } from "../types";
import type { RawZone } from "./zones";

export interface EmaSnapshot {
  ema50: number | null;
  ema100: number | null;
  ema200: number | null;
}

export interface ScoreContext {
  candles: Candle[];
  atr: number;
  volumeSma: number[];
  emas: EmaSnapshot;
  profile: VolumeProfile;
  higherZones: { timeframe: Timeframe; zoneLow: number; zoneHigh: number; kind: RawZone["kind"] }[];
}

const TOUCH_CAP = 8;
const REJECTION_CAP_PCT = 12;
const AGE_FULL_BARS = 250;

export function scoreZone(raw: RawZone, context: ScoreContext): Zone {
  const touches = countTouches(context.candles, raw);
  const rejection = measureRejection(context.candles, raw);
  const touchScore = clamp((Math.min(touches, TOUCH_CAP) / TOUCH_CAP) * 25, 0, 25);
  const rejectionScore = clamp((Math.min(rejection, REJECTION_CAP_PCT) / REJECTION_CAP_PCT) * 25, 0, 25);
  const volumeScore = scoreVolume(raw.pivots, context);
  const ageScore = scoreAge(context.candles, raw);
  const timeframe = scoreTimeframes(raw, context);
  const ema = scoreEma(raw, context);

  const score = clamp(
    touchScore + rejectionScore + volumeScore + ageScore + timeframe.score + ema.score,
    0,
    100,
  );

  return {
    id: `${raw.kind}-${raw.zoneLow.toFixed(2)}-${raw.zoneHigh.toFixed(2)}`,
    kind: raw.kind,
    zoneLow: timeframe.zoneLow,
    zoneHigh: timeframe.zoneHigh,
    centerPrice: (timeframe.zoneLow + timeframe.zoneHigh) / 2,
    pivots: raw.pivots,
    score,
    tier: tierFor(score),
    touchCount: touches,
    touchScore,
    rejectionScore,
    maxRejectionPct: rejection,
    volumeScore,
    ageScore,
    timeframeScore: timeframe.score,
    emaScore: ema.score,
    emaConfluence: ema.labels.length > 0,
    emaLabels: ema.labels,
    multiTimeframe: timeframe.timeframes.length > 1,
    timeframes: timeframe.timeframes,
    ...profileConfluence(
      { zoneLow: timeframe.zoneLow, zoneHigh: timeframe.zoneHigh },
      context.profile,
    ),
    firstIndex: raw.firstIndex,
    lastIndex: raw.lastIndex,
  };
}

export function tierFor(score: number): ZoneTier {
  if (score >= 75) return "strong";
  if (score >= 50) return "medium";
  return "weak";
}

function countTouches(candles: Candle[], zone: RawZone): number {
  let touches = 0;
  let outside = true;
  for (let i = zone.firstIndex; i < candles.length; i++) {
    const candle = candles[i];
    if (!candle) continue;
    const overlaps = candle.low <= zone.zoneHigh && candle.high >= zone.zoneLow;
    if (overlaps && outside) {
      touches += 1;
      outside = false;
    } else if (!overlaps) {
      outside = true;
    }
  }
  return touches;
}

function measureRejection(candles: Candle[], zone: RawZone): number {
  let maxMove = 0;
  let i = zone.firstIndex;
  while (i < candles.length) {
    const candle = candles[i];
    if (!candle || !overlaps(candle, zone)) {
      i += 1;
      continue;
    }
    let exit = i;
    while (exit < candles.length && candles[exit] && overlaps(candles[exit] as Candle, zone)) exit += 1;
    if (zone.kind === "support") {
      let peak = zone.zoneHigh;
      for (let k = exit; k < candles.length; k++) {
        const bar = candles[k];
        if (!bar || overlaps(bar, zone)) break;
        peak = Math.max(peak, bar.high);
      }
      maxMove = Math.max(maxMove, ((peak - zone.zoneHigh) / zone.zoneHigh) * 100);
    } else {
      let trough = zone.zoneLow;
      for (let k = exit; k < candles.length; k++) {
        const bar = candles[k];
        if (!bar || overlaps(bar, zone)) break;
        trough = Math.min(trough, bar.low);
      }
      maxMove = Math.max(maxMove, ((zone.zoneLow - trough) / zone.zoneLow) * 100);
    }
    i = Math.max(exit, i + 1);
  }
  return maxMove;
}

function overlaps(candle: Candle, zone: RawZone): boolean {
  return candle.low <= zone.zoneHigh && candle.high >= zone.zoneLow;
}

function scoreVolume(pivots: Pivot[], context: ScoreContext): number {
  if (pivots.length === 0) return 0;
  let ratioSum = 0;
  let counted = 0;
  for (const pivot of pivots) {
    const average = context.volumeSma[pivot.index] ?? 0;
    if (!(average > 0)) continue;
    ratioSum += pivot.volume / average;
    counted += 1;
  }
  const ratio = counted > 0 ? ratioSum / counted : 1;
  let score = clamp(((Math.min(ratio, 2) - 0.5) / 1.5) * 16, 0, 16);
  const zone = {
    zoneLow: Math.min(...pivots.map((pivot) => pivot.price)),
    zoneHigh: Math.max(...pivots.map((pivot) => pivot.price)),
  };
  const confluence = profileConfluence(zone, context.profile);
  if (confluence.pocConfluence) score += 4;
  else if (confluence.hvnConfluence) score += 2;
  return clamp(score, 0, 20);
}

function scoreAge(candles: Candle[], zone: RawZone): number {
  const bars = Math.max(0, candles.length - 1 - zone.firstIndex);
  if (bars < 15) return clamp((bars / 15) * 3, 0, 3);
  const respected = !isBroken(candles, zone);
  const span = clamp(bars / AGE_FULL_BARS, 0, 1);
  return clamp(span * 10 * (respected ? 1 : 0.45), 0, 10);
}

function isBroken(candles: Candle[], zone: RawZone): boolean {
  const last = candles[candles.length - 1];
  if (!last) return false;
  if (zone.kind === "support") return last.close < zone.zoneLow;
  return last.close > zone.zoneHigh;
}

function scoreTimeframes(raw: RawZone, context: ScoreContext) {
  const timeframes: Timeframe[] = ["D"];
  let zoneLow = raw.zoneLow;
  let zoneHigh = raw.zoneHigh;
  const slack = context.atr * 0.5;
  for (const higher of context.higherZones) {
    if (higher.kind !== raw.kind) continue;
    const gap =
      raw.zoneLow > higher.zoneHigh
        ? raw.zoneLow - higher.zoneHigh
        : higher.zoneLow > raw.zoneHigh
          ? higher.zoneLow - raw.zoneHigh
          : 0;
    if (gap > slack) continue;
    if (!timeframes.includes(higher.timeframe)) timeframes.push(higher.timeframe);
    zoneLow = Math.min(zoneLow, higher.zoneLow);
    zoneHigh = Math.max(zoneHigh, higher.zoneHigh);
  }
  const score = timeframes.length >= 3 ? 10 : timeframes.length === 2 ? 6 : 2;
  return { score, timeframes, zoneLow, zoneHigh };
}

function scoreEma(raw: RawZone, context: ScoreContext) {
  const labels: string[] = [];
  const near = (value: number | null, label: string) => {
    if (value == null || !Number.isFinite(value)) return;
    const inside = value >= raw.zoneLow && value <= raw.zoneHigh;
    const distance = inside ? 0 : value < raw.zoneLow ? raw.zoneLow - value : value - raw.zoneHigh;
    if (distance < context.atr * 0.3) labels.push(label);
  };
  near(context.emas.ema50, "EMA50");
  near(context.emas.ema100, "EMA100");
  near(context.emas.ema200, "EMA200");
  const score = labels.length >= 3 ? 10 : labels.length === 2 ? 8 : labels.length === 1 ? 6 : 0;
  return { score, labels };
}
