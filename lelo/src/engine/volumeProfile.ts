import type { Candle, VolumeNode, VolumeProfile, Zone } from "../types";

const BIN_COUNT = 64;

export function buildVolumeProfile(candles: Candle[]): VolumeProfile {
  if (candles.length === 0) {
    return { nodes: [], poc: null, hvn: [], lvn: [] };
  }
  let min = Infinity;
  let max = -Infinity;
  for (const candle of candles) {
    if (candle.low < min) min = candle.low;
    if (candle.high > max) max = candle.high;
  }
  if (!Number.isFinite(min) || !Number.isFinite(max) || max <= min) {
    return { nodes: [], poc: null, hvn: [], lvn: [] };
  }
  const step = (max - min) / BIN_COUNT;
  const volumes = new Array<number>(BIN_COUNT).fill(0);
  for (const candle of candles) {
    const start = clampBin(Math.floor((candle.low - min) / step));
    const end = clampBin(Math.floor((Math.max(candle.high, candle.low) - min) / step));
    const span = end - start + 1;
    const share = candle.volume / span;
    for (let i = start; i <= end; i++) volumes[i] = (volumes[i] ?? 0) + share;
  }

  let pocIndex = 0;
  for (let i = 1; i < BIN_COUNT; i++) {
    if ((volumes[i] ?? 0) > (volumes[pocIndex] ?? 0)) pocIndex = i;
  }
  const sorted = [...volumes].sort((a, b) => a - b);
  const highCut = sorted[Math.floor(BIN_COUNT * 0.72)] ?? 0;
  const lowCut = sorted[Math.floor(BIN_COUNT * 0.28)] ?? 0;

  const nodes: VolumeNode[] = volumes.map((volume, index) => {
    const priceLow = min + index * step;
    const priceHigh = priceLow + step;
    let kind: VolumeNode["kind"] = "normal";
    if (index === pocIndex) kind = "poc";
    else if (volume >= highCut && isLocalExtreme(volumes, index, "max")) kind = "hvn";
    else if (volume <= lowCut && isLocalExtreme(volumes, index, "min")) kind = "lvn";
    return {
      price: (priceLow + priceHigh) / 2,
      priceLow,
      priceHigh,
      volume,
      kind,
    };
  });

  const poc = nodes[pocIndex] ?? null;
  const hvn = topNodes(nodes.filter((node) => node.kind === "hvn"), 3);
  const lvn = topNodes(
    nodes.filter((node) => node.kind === "lvn"),
    3,
    true,
  );
  return { nodes, poc, hvn, lvn };
}

function clampBin(index: number): number {
  return Math.min(BIN_COUNT - 1, Math.max(0, index));
}

function isLocalExtreme(volumes: number[], index: number, mode: "max" | "min"): boolean {
  const value = volumes[index] ?? 0;
  const left = volumes[index - 1] ?? value;
  const right = volumes[index + 1] ?? value;
  return mode === "max" ? value >= left && value >= right : value <= left && value <= right;
}

function topNodes(nodes: VolumeNode[], count: number, lowest = false): VolumeNode[] {
  const sorted = [...nodes].sort((a, b) => (lowest ? a.volume - b.volume : b.volume - a.volume));
  return sorted.slice(0, count);
}

export function profileConfluence(zone: Pick<Zone, "zoneLow" | "zoneHigh">, profile: VolumeProfile) {
  const overlaps = (node: VolumeNode | null | undefined) =>
    !!node && zone.zoneLow <= node.priceHigh && zone.zoneHigh >= node.priceLow;
  return {
    pocConfluence: overlaps(profile.poc),
    hvnConfluence: profile.hvn.some((node) => overlaps(node)),
    lvnConfluence: profile.lvn.some((node) => overlaps(node)),
  };
}
