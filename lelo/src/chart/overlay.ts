import type { IChartApi, ISeriesApi, UTCTimestamp } from "lightweight-charts";
import type { Analysis, Candle } from "../types";
import { drawDrawings, type Drawing } from "./drawings";

export interface OverlayFlags {
  support: boolean;
  resistance: boolean;
  orderBlocks: boolean;
  fvg: boolean;
  liquidity: boolean;
  poc: boolean;
  ema50: boolean;
  ema100: boolean;
  ema200: boolean;
  bos: boolean;
  choch: boolean;
}

export const defaultOverlays: OverlayFlags = {
  support: true,
  resistance: true,
  orderBlocks: true,
  fvg: true,
  liquidity: true,
  poc: true,
  ema50: true,
  ema100: true,
  ema200: true,
  bos: true,
  choch: true,
};

export function drawOverlay(
  canvas: HTMLCanvasElement,
  chart: IChartApi,
  series: ISeriesApi<"Candlestick">,
  candles: Candle[],
  analysis: Analysis,
  flags: OverlayFlags,
  drawings: Drawing[] = [],
) {
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  const paneWidth = Math.max(0, width - chart.priceScale("right").width());
  const paneHeight = Math.max(0, height - chart.timeScale().height());

  const xOf = (timestamp: number) => chart.timeScale().timeToCoordinate((timestamp / 1000) as UTCTimestamp);
  const yOf = (price: number) => series.priceToCoordinate(price);

  if (flags.support) paintZones(ctx, analysis.supports, "#3dd68c", paneWidth, xOf, yOf);
  if (flags.resistance) paintZones(ctx, analysis.resistances, "#ff5d5d", paneWidth, xOf, yOf);
  if (flags.orderBlocks) {
    for (const block of analysis.orderBlocks) {
      const candle = candles[block.index];
      paintBand(ctx, block.priceRange.high, block.priceRange.low, candle ? xOf(candle.timestamp) ?? 0 : 0, paneWidth, block.type === "bullish" ? "rgba(38,166,154,0.22)" : "rgba(239,83,80,0.20)", yOf);
    }
  }
  if (flags.fvg) {
    for (const gap of analysis.fairValueGaps) {
      paintBand(ctx, gap.zoneHigh, gap.zoneLow, xOf(gap.timestamp) ?? 0, paneWidth, gap.type === "bullish" ? "rgba(66,165,245,0.16)" : "rgba(171,71,188,0.16)", yOf);
    }
  }
  if (flags.liquidity) {
    for (const pool of analysis.liquidity) {
      const y = yOf(pool.price);
      if (y == null) continue;
      ctx.save();
      ctx.strokeStyle = pool.swept ? "#f5c542" : "rgba(245,197,66,0.55)";
      ctx.setLineDash(pool.swept ? [] : [5, 4]);
      ctx.lineWidth = pool.swept ? 1.5 : 1;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(paneWidth, y);
      ctx.stroke();
      ctx.restore();
    }
  }
  if (flags.poc && analysis.profile.poc) {
    const node = analysis.profile.poc;
    paintBand(ctx, node.priceHigh, node.priceLow, 0, paneWidth, "rgba(245,197,66,0.16)", yOf);
    const y = yOf(node.price);
    if (y != null) {
      ctx.strokeStyle = "#f5c542";
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(paneWidth, y);
      ctx.stroke();
      label(ctx, "POC", paneWidth - 36, y - 4, "#f5c542");
    }
  }
  for (const node of flags.poc ? analysis.profile.hvn : []) {
    paintBand(ctx, node.priceHigh, node.priceLow, 0, paneWidth, "rgba(96,165,250,0.08)", yOf);
  }
  for (const node of flags.poc ? analysis.profile.lvn : []) {
    paintBand(ctx, node.priceHigh, node.priceLow, 0, paneWidth, "rgba(148,163,184,0.08)", yOf);
  }
  drawDrawings(ctx, drawings, xOf, yOf, paneWidth);
  ctx.clearRect(paneWidth, 0, width - paneWidth, height);
  ctx.clearRect(0, paneHeight, width, height - paneHeight);
}

function paintZones(
  ctx: CanvasRenderingContext2D,
  zones: Analysis["supports"],
  color: string,
  paneWidth: number,
  xOf: (timestamp: number) => number | null,
  yOf: (price: number) => number | null,
) {
  for (const zone of zones) {
    const start = zone.pivots[0] ? xOf(zone.pivots[0].timestamp) : 0;
    paintBand(ctx, zone.zoneHigh, zone.zoneLow, start ?? 0, paneWidth, hexAlpha(color, 0.14), yOf);
    const y = yOf(zone.zoneHigh);
    if (y != null) label(ctx, `${Math.round(zone.score)}%`, 8, y + 12, color);
  }
}

function paintBand(
  ctx: CanvasRenderingContext2D,
  high: number,
  low: number,
  x: number,
  paneWidth: number,
  fill: string,
  yOf: (price: number) => number | null,
) {
  const y1 = yOf(high);
  const y2 = yOf(low);
  if (y1 == null || y2 == null) return;
  const top = Math.min(y1, y2);
  const height = Math.max(2, Math.abs(y2 - y1));
  ctx.fillStyle = fill;
  ctx.fillRect(Math.max(0, x), top, paneWidth - Math.max(0, x), height);
  ctx.strokeStyle = fill.startsWith("rgba") ? fill.replace(/[\d.]+\)$/, "0.9)") : fill;
  ctx.lineWidth = 1;
  ctx.strokeRect(Math.max(0, x), top, paneWidth - Math.max(0, x), height);
}

function label(ctx: CanvasRenderingContext2D, text: string, x: number, y: number, color: string) {
  ctx.font = "11px IBM Plex Sans, sans-serif";
  ctx.fillStyle = color;
  ctx.fillText(text, x, y);
}

function hexAlpha(hex: string, alpha: number): string {
  const value = hex.replace("#", "");
  const r = Number.parseInt(value.slice(0, 2), 16);
  const g = Number.parseInt(value.slice(2, 4), 16);
  const b = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}
