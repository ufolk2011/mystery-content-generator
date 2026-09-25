import type { UTCTimestamp } from "lightweight-charts";

export type DrawingTool = "cursor" | "trend" | "hline" | "rect" | "arrow" | "text" | "fib" | "delete";

export interface ChartPoint {
  time: number;
  price: number;
}

export interface Drawing {
  id: string;
  type: Exclude<DrawingTool, "cursor" | "delete">;
  a: ChartPoint;
  b?: ChartPoint;
  text?: string;
}

const FIB_LEVELS = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];

export function drawDrawings(
  ctx: CanvasRenderingContext2D,
  drawings: Drawing[],
  xOf: (timestamp: number) => number | null,
  yOf: (price: number) => number | null,
  paneWidth: number,
) {
  ctx.save();
  ctx.lineWidth = 1.5;
  ctx.font = "12px IBM Plex Sans, sans-serif";
  for (const drawing of drawings) {
    const x1 = xOf(drawing.a.time);
    const y1 = yOf(drawing.a.price);
    const x2 = drawing.b ? xOf(drawing.b.time) : x1;
    const y2 = drawing.b ? yOf(drawing.b.price) : y1;
    if (x1 == null || y1 == null || x2 == null || y2 == null) continue;
    ctx.strokeStyle = "#d6dde6";
    ctx.fillStyle = "rgba(214,221,230,0.08)";
    if (drawing.type === "hline") {
      ctx.beginPath();
      ctx.moveTo(0, y1);
      ctx.lineTo(paneWidth, y1);
      ctx.stroke();
      ctx.fillStyle = "#d6dde6";
      ctx.fillText(drawing.a.price.toFixed(2), 8, y1 - 4);
    } else if (drawing.type === "trend" || drawing.type === "arrow") {
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
      if (drawing.type === "arrow") strokeArrow(ctx, x1, y1, x2, y2);
    } else if (drawing.type === "rect") {
      ctx.fillRect(Math.min(x1, x2), Math.min(y1, y2), Math.abs(x2 - x1), Math.abs(y2 - y1));
      ctx.strokeRect(Math.min(x1, x2), Math.min(y1, y2), Math.abs(x2 - x1), Math.abs(y2 - y1));
    } else if (drawing.type === "text") {
      ctx.fillStyle = "#f5c542";
      ctx.fillText(drawing.text || "Text", x1, y1);
    } else if (drawing.type === "fib" && drawing.b) {
      const high = Math.max(drawing.a.price, drawing.b.price);
      const low = Math.min(drawing.a.price, drawing.b.price);
      for (const level of FIB_LEVELS) {
        const price = high - (high - low) * level;
        const y = yOf(price);
        if (y == null) continue;
        ctx.strokeStyle = "rgba(245,197,66,0.85)";
        ctx.beginPath();
        ctx.moveTo(Math.min(x1, x2), y);
        ctx.lineTo(Math.max(x1, x2), y);
        ctx.stroke();
        ctx.fillStyle = "#f5c542";
        ctx.fillText(`${(level * 100).toFixed(1)}%  ${price.toFixed(2)}`, Math.min(x1, x2) + 6, y - 3);
      }
    }
  }
  ctx.restore();
}

export function hitDrawing(
  drawing: Drawing,
  x: number,
  y: number,
  xOf: (timestamp: number) => number | null,
  yOf: (price: number) => number | null,
): boolean {
  const x1 = xOf(drawing.a.time);
  const y1 = yOf(drawing.a.price);
  if (x1 == null || y1 == null) return false;
  if (drawing.type === "hline") return Math.abs(y - y1) < 6;
  if (drawing.type === "text") return Math.abs(x - x1) < 40 && Math.abs(y - y1) < 12;
  const x2 = drawing.b ? xOf(drawing.b.time) : x1;
  const y2 = drawing.b ? yOf(drawing.b.price) : y1;
  if (x2 == null || y2 == null) return false;
  if (drawing.type === "rect" || drawing.type === "fib") {
    return x >= Math.min(x1, x2) - 4 && x <= Math.max(x1, x2) + 4 && y >= Math.min(y1, y2) - 4 && y <= Math.max(y1, y2) + 4;
  }
  return distanceToSegment(x, y, x1, y1, x2, y2) < 7;
}

export function timeFromCoordinate(time: number | string | { year: number; month: number; day: number }): number {
  if (typeof time === "number") return time * 1000;
  if (typeof time === "string") return Date.parse(time);
  return Date.UTC(time.year, time.month - 1, time.day);
}

export function asTimestamp(time: number): UTCTimestamp {
  return (time / 1000) as UTCTimestamp;
}

function strokeArrow(ctx: CanvasRenderingContext2D, x1: number, y1: number, x2: number, y2: number) {
  const angle = Math.atan2(y2 - y1, x2 - x1);
  const size = 10;
  ctx.beginPath();
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - size * Math.cos(angle - 0.4), y2 - size * Math.sin(angle - 0.4));
  ctx.moveTo(x2, y2);
  ctx.lineTo(x2 - size * Math.cos(angle + 0.4), y2 - size * Math.sin(angle + 0.4));
  ctx.stroke();
}

function distanceToSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number) {
  const dx = x2 - x1;
  const dy = y2 - y1;
  const length = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((px - x1) * dx + (py - y1) * dy) / length));
  return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
}
