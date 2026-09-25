import type { Pivot, ZoneKind } from "../types";

export interface RawZone {
  kind: ZoneKind;
  zoneLow: number;
  zoneHigh: number;
  centerPrice: number;
  pivots: Pivot[];
  firstIndex: number;
  lastIndex: number;
}

/** Merge pivots whose prices sit within `threshold` into a single zone. */
export function clusterPivots(pivots: Pivot[], threshold: number, kind: ZoneKind): RawZone[] {
  const sorted = [...pivots].sort((a, b) => a.price - b.price || a.index - b.index);
  const groups: Pivot[][] = [];
  for (const pivot of sorted) {
    const last = groups[groups.length - 1];
    const edge = last?.reduce((max, item) => Math.max(max, item.price), -Infinity) ?? -Infinity;
    if (last && pivot.price - edge <= threshold) last.push(pivot);
    else groups.push([pivot]);
  }
  return groups.map((group) => toRawZone(group, kind, threshold));
}

function toRawZone(group: Pivot[], kind: ZoneKind, threshold: number): RawZone {
  const prices = group.map((pivot) => pivot.price);
  let zoneLow = Math.min(...prices);
  let zoneHigh = Math.max(...prices);
  const minThickness = Math.max(threshold * 0.16, zoneLow * 0.001);
  if (zoneHigh - zoneLow < minThickness) {
    const pad = minThickness / 2;
    const center = (zoneLow + zoneHigh) / 2;
    zoneLow = center - pad;
    zoneHigh = center + pad;
  }
  const indexes = group.map((pivot) => pivot.index);
  return {
    kind,
    zoneLow,
    zoneHigh,
    centerPrice: (zoneLow + zoneHigh) / 2,
    pivots: group,
    firstIndex: Math.min(...indexes),
    lastIndex: Math.max(...indexes),
  };
}

export function rangesOverlap(aLow: number, aHigh: number, bLow: number, bHigh: number, slack = 0): boolean {
  return aLow <= bHigh + slack && bLow <= aHigh + slack;
}
