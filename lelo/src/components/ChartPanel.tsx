import { useEffect, useRef, useState } from "react";
import {
  ColorType,
  CrosshairMode,
  LineStyle,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { OverlayFlags } from "../chart/overlay";
import { drawOverlay } from "../chart/overlay";
import { hitDrawing, timeFromCoordinate, type Drawing, type DrawingTool } from "../chart/drawings";
import type { QuoteSeries } from "../data/yahoo";
import { heikinAshi } from "../engine";
import type { Analysis, Candle, PivotStrength } from "../types";
import type { HistoryRange } from "../data/yahoo";

const RIGHT_GAP_PX = 300;
const TOOLS: { id: DrawingTool; label: string }[] = [
  { id: "cursor", label: "Cursor" },
  { id: "trend", label: "Trend Line" },
  { id: "hline", label: "Horizontal Line" },
  { id: "rect", label: "Rectangle" },
  { id: "arrow", label: "Arrow" },
  { id: "text", label: "Text" },
  { id: "fib", label: "Fibonacci" },
  { id: "delete", label: "Delete" },
];

interface Props {
  series: QuoteSeries | null;
  analysis: Analysis | null;
  mode: "candle" | "heikin";
  overlays: OverlayFlags;
  loading: boolean;
  range: HistoryRange;
  strength: PivotStrength;
  onMode: (mode: "candle" | "heikin") => void;
  onRange: (range: HistoryRange) => void;
  onStrength: (strength: PivotStrength) => void;
  onOverlays: (next: OverlayFlags) => void;
}

export function ChartPanel(props: Props) {
  const { series, analysis, mode, overlays, loading, onOverlays } = props;
  const hostRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const emaRefs = useRef<{ ema50: ISeriesApi<"Line"> | null; ema100: ISeriesApi<"Line"> | null; ema200: ISeriesApi<"Line"> | null }>({
    ema50: null,
    ema100: null,
    ema200: null,
  });
  const frameRef = useRef<{ candles: Candle[]; analysis: Analysis; overlays: OverlayFlags; drawings: Drawing[] } | null>(null);
  const drawingsRef = useRef<Drawing[]>([]);
  const draftRef = useRef<Drawing | null>(null);
  const toolRef = useRef<DrawingTool>("cursor");
  const [tool, setTool] = useState<DrawingTool>("cursor");
  const [toolbarOpen, setToolbarOpen] = useState(true);
  const [indicatorsOpen, setIndicatorsOpen] = useState(false);
  const [textPrompt, setTextPrompt] = useState<{ x: number; y: number; drawingId: string } | null>(null);

  useEffect(() => {
    toolRef.current = tool;
    const chart = chartRef.current;
    if (!chart) return;
    chart.applyOptions({
      handleScroll: { pressedMouseMove: tool === "cursor", mouseWheel: true, horzTouchDrag: true, vertTouchDrag: false },
    });
  }, [tool]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const chart = createChart(host, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "#0c1016" }, textColor: "#b7c0cc", fontFamily: "IBM Plex Sans, Noto Sans Thai, sans-serif" },
      grid: { vertLines: { color: "#1c2533" }, horzLines: { color: "#1c2533" } },
      rightPriceScale: { borderColor: "#2a3544" },
      timeScale: {
        borderColor: "#2a3544",
        rightOffset: gapBars(6),
        barSpacing: 6,
        minBarSpacing: 2,
        shiftVisibleRangeOnNewBar: true,
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#758696", width: 1, style: LineStyle.LargeDashed, labelBackgroundColor: "#2a2e39" },
        horzLine: { color: "#758696", width: 1, style: LineStyle.LargeDashed, labelBackgroundColor: "#2a2e39" },
      },
      kineticScroll: { mouse: true, touch: true },
      handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
      handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: { time: true, price: true } },
    });
    const candles = chart.addCandlestickSeries({
      upColor: "#089981",
      downColor: "#f23645",
      borderVisible: false,
      wickUpColor: "#089981",
      wickDownColor: "#f23645",
    });
    emaRefs.current = {
      ema50: chart.addLineSeries({ color: "#f5c542", lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
      ema100: chart.addLineSeries({ color: "#60a5fa", lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
      ema200: chart.addLineSeries({ color: "#e879f9", lineWidth: 2, priceLineVisible: false, lastValueVisible: false }),
    };
    chartRef.current = chart;
    candleRef.current = candles;
    let lastSpacing = 6;
    const paint = () => {
      const spacing = chart.timeScale().options().barSpacing;
      if (Math.abs(spacing - lastSpacing) > 0.2) {
        lastSpacing = spacing;
        chart.timeScale().applyOptions({ rightOffset: gapBars(spacing) });
      }
      const frame = frameRef.current;
      if (!frame) return;
      redraw(canvasRef.current, chart, candles, frame.candles, frame.analysis, frame.overlays, frame.drawings);
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(paint);
    const observer = new ResizeObserver(paint);
    observer.observe(host);
    const onDoubleClick = () => {
      chart.timeScale().applyOptions({ barSpacing: 6, rightOffset: gapBars(6) });
      const total = frameRef.current?.candles.length ?? 0;
      if (total > 0) chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, total - 180), to: total + gapBars(6) });
    };
    host.addEventListener("dblclick", onDoubleClick);
    return () => {
      host.removeEventListener("dblclick", onDoubleClick);
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    const candleSeries = candleRef.current;
    if (!chart || !candleSeries || !series || !analysis) return;
    const display = mode === "heikin" ? heikinAshi(series.candles) : series.candles;
    candleSeries.setData(toBars(display));
    const total = display.length;
    const offset = gapBars(chart.timeScale().options().barSpacing);
    chart.timeScale().applyOptions({ rightOffset: offset });
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, total - 180), to: total + offset });
  }, [series, mode]);

  useEffect(() => {
    const chart = chartRef.current;
    const candleSeries = candleRef.current;
    if (!chart || !candleSeries || !series || !analysis) return;
    frameRef.current = { candles: series.candles, analysis, overlays, drawings: [...drawingsRef.current, ...(draftRef.current ? [draftRef.current] : [])] };
    setLine(emaRefs.current.ema50, series.candles, analysis.ema50, overlays.ema50);
    setLine(emaRefs.current.ema100, series.candles, analysis.ema100, overlays.ema100);
    setLine(emaRefs.current.ema200, series.candles, analysis.ema200, overlays.ema200);
    candleSeries.setMarkers(markers(analysis, overlays));
    redraw(canvasRef.current, chart, candleSeries, series.candles, analysis, overlays, frameRef.current.drawings);
  }, [series, analysis, overlays, mode]);

  const syncDrawings = () => {
    const chart = chartRef.current;
    const candleSeries = candleRef.current;
    const frame = frameRef.current;
    if (!chart || !candleSeries || !frame) return;
    frame.drawings = [...drawingsRef.current, ...(draftRef.current ? [draftRef.current] : [])];
    redraw(canvasRef.current, chart, candleSeries, frame.candles, frame.analysis, frame.overlays, frame.drawings);
  };

  const pointerPoint = (event: React.PointerEvent) => {
    const chart = chartRef.current;
    const candleSeries = candleRef.current;
    const host = hostRef.current;
    if (!chart || !candleSeries || !host) return null;
    const rect = host.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const time = chart.timeScale().coordinateToTime(x);
    const price = candleSeries.coordinateToPrice(y);
    if (time == null || price == null) return null;
    return { x, y, point: { time: timeFromCoordinate(time), price } };
  };

  return (
    <div className={`chart-shell ${tool === "cursor" ? "" : "drawing"}`}>
      {loading ? <div className="loading">Loading chart</div> : null}
      <div className={`chart-tools ${toolbarOpen ? "open" : ""}`}>
        <button className="tool-collapse" onClick={() => setToolbarOpen((open) => !open)} aria-label="Collapse toolbar">
          {toolbarOpen ? "⟨" : "⟩"}
        </button>
        {toolbarOpen
          ? TOOLS.map((item) => (
              <button key={item.id} className={tool === item.id ? "on" : ""} title={item.label} onClick={() => setTool(item.id)}>
                {toolIcon(item.id)}
              </button>
            ))
          : null}
      </div>
      <div className="chart-indicators">
        <button className={indicatorsOpen ? "on" : ""} onClick={() => setIndicatorsOpen((open) => !open)}>Indicators</button>
        {indicatorsOpen ? <IndicatorMenu overlays={overlays} onChange={onOverlays} /> : null}
      </div>
      <ChartMeta {...props} />
      <div ref={hostRef} className="chart-host" />
      <canvas
        ref={canvasRef}
        className="overlay"
        onPointerDown={(event) => {
          if (toolRef.current === "cursor") return;
          const hit = pointerPoint(event);
          if (!hit) return;
          if (toolRef.current === "delete") {
            const chart = chartRef.current;
            const candleSeries = candleRef.current;
            if (!chart || !candleSeries) return;
            const xOf = (timestamp: number) => chart.timeScale().timeToCoordinate((timestamp / 1000) as UTCTimestamp);
            const yOf = (price: number) => candleSeries.priceToCoordinate(price);
            drawingsRef.current = drawingsRef.current.filter((drawing) => !hitDrawing(drawing, hit.x, hit.y, xOf, yOf));
            syncDrawings();
            return;
          }
          const id = crypto.randomUUID();
          if (toolRef.current === "hline") {
            drawingsRef.current = [...drawingsRef.current, { id, type: "hline", a: hit.point }];
            syncDrawings();
            return;
          }
          if (toolRef.current === "text") {
            const drawing: Drawing = { id, type: "text", a: hit.point, text: "" };
            drawingsRef.current = [...drawingsRef.current, drawing];
            setTextPrompt({ x: hit.x, y: hit.y, drawingId: id });
            syncDrawings();
            return;
          }
          draftRef.current = { id, type: toolRef.current, a: hit.point, b: hit.point };
          syncDrawings();
        }}
        onPointerMove={(event) => {
          if (!draftRef.current) return;
          const hit = pointerPoint(event);
          if (!hit) return;
          draftRef.current = { ...draftRef.current, b: hit.point };
          syncDrawings();
        }}
        onPointerUp={() => {
          if (!draftRef.current) return;
          drawingsRef.current = [...drawingsRef.current, draftRef.current];
          draftRef.current = null;
          syncDrawings();
        }}
      />
      {textPrompt ? (
        <form
          className="text-pop"
          style={{ left: textPrompt.x, top: textPrompt.y }}
          onSubmit={(event) => {
            event.preventDefault();
            const input = new FormData(event.currentTarget).get("label");
            drawingsRef.current = drawingsRef.current.map((drawing) =>
              drawing.id === textPrompt.drawingId ? { ...drawing, text: String(input || "Note") } : drawing,
            );
            setTextPrompt(null);
            syncDrawings();
          }}
        >
          <input name="label" autoFocus placeholder="Label" />
        </form>
      ) : null}
    </div>
  );
}

function ChartMeta({ range, strength, mode, onRange, onMode, onStrength, series }: Props) {
  return (
    <div className="chart-meta">
      <strong>{series?.symbol ?? ""}</strong>
      <em>{series ? `$${series.price.toFixed(2)}` : ""}</em>
      <b className={series && series.change >= 0 ? "up" : "down"}>
        {series ? `${series.change >= 0 ? "+" : ""}${series.changePercent.toFixed(2)}%` : ""}
      </b>
      <span className="meta-gap" />
      {(["1y", "2y", "5y", "10y"] as HistoryRange[]).map((item) => (
        <button key={item} className={range === item ? "on" : ""} onClick={() => onRange(item)}>{item.toUpperCase()}</button>
      ))}
      <button className={mode === "candle" ? "on" : ""} onClick={() => onMode("candle")}>Candles</button>
      <button className={mode === "heikin" ? "on" : ""} onClick={() => onMode("heikin")}>Heikin Ashi</button>
      {([3, 5, 10, 20] as PivotStrength[]).map((value) => (
        <button key={value} className={strength === value ? "on" : ""} onClick={() => onStrength(value)} title="Pivot strength">{value}</button>
      ))}
    </div>
  );
}

function IndicatorMenu({ overlays, onChange }: { overlays: OverlayFlags; onChange: (next: OverlayFlags) => void }) {
  const items: { key: keyof OverlayFlags; label: string }[] = [
    { key: "ema50", label: "EMA50" },
    { key: "ema100", label: "EMA100" },
    { key: "ema200", label: "EMA200" },
    { key: "support", label: "Support Zones" },
    { key: "resistance", label: "Resistance Zones" },
    { key: "poc", label: "Volume Profile" },
    { key: "orderBlocks", label: "Order Blocks" },
    { key: "fvg", label: "FVG" },
    { key: "liquidity", label: "Liquidity Zones" },
    { key: "bos", label: "BOS" },
    { key: "choch", label: "CHOCH" },
  ];
  return (
    <div className="indicator-menu">
      {items.map((item) => (
        <label key={item.key}>
          <input
            type="checkbox"
            checked={overlays[item.key]}
            onChange={() => onChange({ ...overlays, [item.key]: !overlays[item.key] })}
          />
          {item.label}
        </label>
      ))}
    </div>
  );
}

function gapBars(barSpacing: number): number {
  return Math.max(8, Math.round(RIGHT_GAP_PX / Math.max(barSpacing, 1)));
}

function redraw(
  canvas: HTMLCanvasElement | null,
  chart: IChartApi,
  candleSeries: ISeriesApi<"Candlestick">,
  candles: Candle[],
  analysis: Analysis,
  overlays: OverlayFlags,
  drawings: Drawing[],
) {
  if (!canvas) return;
  const parent = canvas.parentElement;
  if (!parent) return;
  const rect = parent.getBoundingClientRect();
  canvas.width = Math.floor(rect.width);
  canvas.height = Math.floor(rect.height);
  drawOverlay(canvas, chart, candleSeries, candles, analysis, overlays, drawings);
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

function toolIcon(tool: DrawingTool): string {
  const icons: Record<DrawingTool, string> = {
    cursor: "↖",
    trend: "╱",
    hline: "—",
    rect: "▢",
    arrow: "➜",
    text: "T",
    fib: "Fib",
    delete: "⌫",
  };
  return icons[tool];
}
