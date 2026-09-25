import type { Analysis, Trend, Zone } from "../types";

export function buildMarketSummary(analysis: Pick<
  Analysis,
  "trend" | "supports" | "resistances" | "lastEma" | "liquidity" | "bos" | "choch"
> & { price: number }): string {
  const { price, trend, supports, resistances, lastEma } = analysis;
  const support = nearestSupport(supports, price);
  const resistance = nearestResistance(resistances, price);
  const lines: string[] = [];

  if (lastEma.ema200 != null) {
    if (price > lastEma.ema200) {
      lines.push("Current price remains above EMA200, indicating medium-term bullish structure.");
    } else if (price < lastEma.ema200) {
      lines.push("Current price remains below EMA200, indicating medium-term bearish structure.");
    } else {
      lines.push("Current price is trading on EMA200, so the medium-term structure is balanced.");
    }
  }

  if (support) {
    lines.push(
      `The nearest support zone is ${formatPair(support)} with a strength score of ${Math.round(support.score)}%.`,
    );
    const notes: string[] = [];
    if (support.emaConfluence) notes.push(support.emaLabels.join(" and "));
    if (support.multiTimeframe) notes.push("multiple timeframes");
    if (support.touchCount > 1) notes.push(`${support.touchCount} historical reactions`);
    if (notes.length > 0) {
      lines.push(`This zone is confirmed by ${notes.join(" and ")}.`);
    }
  }

  if (resistance) {
    lines.push(
      `The nearest resistance zone is ${formatPair(resistance)} with a strength score of ${Math.round(resistance.score)}%.`,
    );
  }

  lines.push(trendSentence(trend, support, resistance));

  const sweep = analysis.liquidity.find((pool) => pool.swept);
  if (sweep) {
    lines.push(
      sweep.type === "equal_highs"
        ? "A liquidity sweep took prior equal highs and closed back below that pool."
        : "A liquidity sweep took prior equal lows and closed back above that pool.",
    );
  }

  const lastChoch = analysis.choch[analysis.choch.length - 1];
  const lastBos = analysis.bos[analysis.bos.length - 1];
  if (lastChoch && (!lastBos || lastChoch.index > lastBos.index)) {
    lines.push(
      `The latest structural shift is a ${lastChoch.direction} change of character at ${lastChoch.price.toFixed(2)}.`,
    );
  } else if (lastBos) {
    lines.push(`The latest break of structure is ${lastBos.direction} at ${lastBos.price.toFixed(2)}.`);
  }

  lines.push("This is a technical-structure reading only. It is not financial advice.");
  return lines.join("\n\n");
}

function nearestSupport(zones: Zone[], price: number): Zone | null {
  const below = zones.filter((zone) => zone.centerPrice <= price);
  const pool = below.length > 0 ? below : zones;
  return [...pool].sort((a, b) => Math.abs(a.centerPrice - price) - Math.abs(b.centerPrice - price))[0] ?? null;
}

function nearestResistance(zones: Zone[], price: number): Zone | null {
  const above = zones.filter((zone) => zone.centerPrice >= price);
  const pool = above.length > 0 ? above : zones;
  return [...pool].sort((a, b) => Math.abs(a.centerPrice - price) - Math.abs(b.centerPrice - price))[0] ?? null;
}

function trendSentence(trend: Trend, support: Zone | null, resistance: Zone | null): string {
  if (trend === "bull") {
    return support
      ? "Market structure remains bullish unless that support is broken."
      : "Market structure remains bullish unless support is broken.";
  }
  if (trend === "bear") {
    return resistance
      ? "Market structure remains bearish unless that resistance is broken."
      : "Market structure remains bearish unless resistance is broken.";
  }
  return "Market structure is range-bound until price leaves the nearest support or resistance zone.";
}

function formatPair(zone: Zone): string {
  return `${formatPrice(zone.zoneLow)}-${formatPrice(zone.zoneHigh)}`;
}

function formatPrice(value: number): string {
  return value >= 100 ? value.toFixed(0) : value.toFixed(2);
}

export function rankZones(zones: Zone[], price: number, kind: Zone["kind"], limit = 3): Zone[] {
  const sided =
    kind === "support"
      ? zones.filter((zone) => zone.centerPrice <= price * 1.02)
      : zones.filter((zone) => zone.centerPrice >= price * 0.98);
  const pool = sided.length > 0 ? sided : zones.filter((zone) => zone.kind === kind);
  const nearby = pool.filter((zone) => Math.abs(zone.centerPrice - price) / Math.max(price, 1) <= 0.35);
  const chosen = nearby.length > 0 ? nearby : [...pool].sort((a, b) => proximity(a, price) - proximity(b, price)).slice(0, 8);
  return [...chosen].sort((a, b) => b.score - a.score || proximity(a, price) - proximity(b, price)).slice(0, limit);
}

function proximity(zone: Zone, price: number): number {
  return Math.abs(zone.centerPrice - price);
}
