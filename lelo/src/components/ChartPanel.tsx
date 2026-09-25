import { useEffect, useRef } from "react";
import { ColorType, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import type { OverlayFlags } from "../chart/overlay";
import { drawOverlay } from "../chart/overlay";
import type { QuoteSeries } from "../data/yahoo";
import { heikinAshi } from "../engine";
import type { Analysis, Candle } from "../types";

interface Props {
  series: QuoteSeries | null;
  analysis: Analysis | null;
  mode: "candle" | "heikin";
  overlays: OverlayFlags;
  loading: boolean;
}

export function ChartPanel({ series, analysis, mode, overlays, loading }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const emaRefs = useRef<{ ema50: ISeriesApi<"Line"> | null; ema100: ISeriesApi<"Line"> | null; ema200: ISeriesApi<"Line"> | null }>({
    ema50: null,
    ema100: null,
    ema200: null,
  });
  const frameRef = useRef<{ candles: Candle[]; analysis: Analysis; overlays: OverlayFlags } | null>(null);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const chart = createChart(host, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "#0c1016" }, textColor: "#93a0b0" },
      grid: { vertLines: { color: "#1a2330" }, horzLines: { color: "#1a2330" } },
      rightPriceScale: { borderColor: "#243140" },
      timeScale: { borderColor: "#243140", rightOffset: 6 },
      crosshair: { vertLine: { color: "#3d4c60" }, horzLine: { color: "#3d4c60" } },
    });
    const candles = chart.addCandlestickSeries({
      upColor: "#3dd68c",
      downColor: "#ff5d5d",
      borderVisible: false,
      wickUpColor: "#3dd68c",
      wickDownColor: "#ff5d5d",
    });
    emaRefs.current = {
      ema50: chart.addLineSeries({ color: "#f5c542", lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
      ema100: chart.addLineSeries({ color: "#60a5fa", lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
      ema200: chart.addLineSeries({ color: "#e879f9", lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
    };
    chartRef.current = chart;
    candleRef.current = candles;
    const paint = () => {
      const frame = frameRef.current;
      if (!frame) return;
      redraw(canvasRef.current, chart, candles, frame.candles, frame.analysis, frame.overlays);
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(paint);
    const observer = new ResizeObserver(paint);
    observer.observe(host);
    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const candleSeries = candleRef.current;
    if (!chart || !candleSeries || !series || !analysis) return;
    frameRef.current = { candles: series.candles, analysis, overlays };
    const display = mode === "heikin" ? heikinAshi(series.candles) : series.candles;
    candleSeries.setData(toBars(display));
    setLine(emaRefs.current.ema50, series.candles, analysis.ema50, overlays.ema50);
    setLine(emaRefs.current.ema100, series.candles, analysis.ema100, overlays.ema100);
    setLine(emaRefs.current.ema200, series.candles, analysis.ema200, overlays.ema200);
    candleSeries.setMarkers(markers(analysis, overlays));
    const total = display.length;
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, total - 220), to: total + 4 });
    const paint = () => redraw(canvasRef.current, chart, candleSeries, series.candles, analysis, overlays);
    paint();
    requestAnimationFrame(() => requestAnimationFrame(paint));
  }, [series, analysis, mode, overlays]);

  return (
    <div className="chart-shell">
      {loading ? <div className="loading">กำลังโหลดกราฟ</div> : null}
      <div ref={hostRef} className="chart-host" />
      <canvas ref={canvasRef} className="overlay" />
    </div>
  );
}

function redraw(
  canvas: HTMLCanvasElement | null,
  chart: IChartApi,
  candleSeries: ISeriesApi<"Candlestick">,
  candles?: Candle[],
  analysis?: Analysis,
  overlays?: OverlayFlags,
) {
  if (!canvas) return;
  const parent = canvas.parentElement;
  if (!parent) return;
  const rect = parent.getBoundingClientRect();
  canvas.width = Math.floor(rect.width);
  canvas.height = Math.floor(rect.height);
  if (candles && analysis && overlays) drawOverlay(canvas, chart, candleSeries, candles, analysis, overlays);
}

function toBars(candles: Candle[]) {
  return candles.map((candle) => ({
    time: (candle.timestamp / 1000) as UTCTimestamp,
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
  }));
}

function setLine(series: ISeriesApi<"Line"> | null, candles: Candle[], values: number[], visible: boolean) {
  if (!series) return;
  if (!visible) {
    series.setData([]);
    return;
  }
  series.setData(
    values.flatMap((value, index) => {
      const candle = candles[index];
      if (!candle || !Number.isFinite(value)) return [];
      return [{ time: (candle.timestamp / 1000) as UTCTimestamp, value }];
    }),
  );
}

function markers(analysis: Analysis, overlays: OverlayFlags) {
  const events = [
    ...(overlays.bos ? analysis.bos.map((event) => ({ ...event, text: "BOS" })) : []),
    ...(overlays.choch ? analysis.choch.map((event) => ({ ...event, text: "CHOCH" })) : []),
    ...(overlays.liquidity
      ? analysis.liquidity
          .filter((pool) => pool.swept && pool.sweepTimestamp && pool.sweepIndex != null)
          .map((pool) => ({
            direction: pool.type === "equal_highs" ? "bearish" as const : "bullish" as const,
            timestamp: pool.sweepTimestamp as number,
            index: pool.sweepIndex as number,
            text: "SWEEP",
          }))
      : []),
  ];
  const seen = new Set<string>();
  return events
    .sort((a, b) => a.index - b.index)
    .filter((event) => {
      const key = `${event.timestamp}-${event.text}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(-24)
    .map((event) => ({
      time: (event.timestamp / 1000) as UTCTimestamp,
      position: event.direction === "bullish" ? "belowBar" as const : "aboveBar" as const,
      color: event.text === "CHOCH" ? "#f5c542" : event.text === "SWEEP" ? "#fb923c" : "#7dd3fc",
      shape: event.direction === "bullish" ? "arrowUp" as const : "arrowDown" as const,
      text: event.text,
    }));
}
