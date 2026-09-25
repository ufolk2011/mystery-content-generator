export interface Candle {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export type PivotType = "high" | "low";

export interface Pivot {
  price: number;
  timestamp: number;
  index: number;
  type: PivotType;
  strength: number;
  volume: number;
}

export type ZoneKind = "support" | "resistance";
export type ZoneTier = "strong" | "medium" | "weak";
export type Timeframe = "D" | "W" | "M";

export interface Zone {
  id: string;
  kind: ZoneKind;
  zoneLow: number;
  zoneHigh: number;
  centerPrice: number;
  pivots: Pivot[];
  score: number;
  tier: ZoneTier;
  touchCount: number;
  touchScore: number;
  rejectionScore: number;
  maxRejectionPct: number;
  volumeScore: number;
  ageScore: number;
  timeframeScore: number;
  emaScore: number;
  emaConfluence: boolean;
  emaLabels: string[];
  multiTimeframe: boolean;
  timeframes: Timeframe[];
  pocConfluence: boolean;
  hvnConfluence: boolean;
  lvnConfluence: boolean;
  firstIndex: number;
  lastIndex: number;
}

export type Trend = "bull" | "bear" | "range";
export type Direction = "bullish" | "bearish";

export interface StructureEvent {
  kind: "bos" | "choch";
  direction: Direction;
  price: number;
  timestamp: number;
  index: number;
}

export interface SwingLabel {
  type: PivotType;
  label: "HH" | "HL" | "LH" | "LL" | "EH" | "EL";
  price: number;
  timestamp: number;
  index: number;
}

export interface LiquidityPool {
  id: string;
  type: "equal_highs" | "equal_lows";
  price: number;
  zoneLow: number;
  zoneHigh: number;
  timestamps: number[];
  indexes: number[];
  swept: boolean;
  sweepTimestamp?: number;
  sweepIndex?: number;
  role: "liquidity_pool" | "stop_hunt" | "sweep";
}

export interface OrderBlock {
  type: "bullish" | "bearish";
  priceRange: { low: number; high: number };
  timestamp: number;
  index: number;
  strength: number;
  mitigated: boolean;
}

export interface FairValueGap {
  type: "bullish" | "bearish";
  zoneLow: number;
  zoneHigh: number;
  timestamp: number;
  index: number;
  filled: boolean;
}

export type VolumeNodeKind = "poc" | "hvn" | "lvn" | "normal";

export interface VolumeNode {
  price: number;
  priceLow: number;
  priceHigh: number;
  volume: number;
  kind: VolumeNodeKind;
}

export interface VolumeProfile {
  nodes: VolumeNode[];
  poc: VolumeNode | null;
  hvn: VolumeNode[];
  lvn: VolumeNode[];
}

export interface Analysis {
  pivots: Pivot[];
  zones: Zone[];
  supports: Zone[];
  resistances: Zone[];
  atr: number;
  ema50: number[];
  ema100: number[];
  ema200: number[];
  lastEma: { ema50: number | null; ema100: number | null; ema200: number | null };
  trend: Trend;
  swings: SwingLabel[];
  bos: StructureEvent[];
  choch: StructureEvent[];
  liquidity: LiquidityPool[];
  orderBlocks: OrderBlock[];
  fairValueGaps: FairValueGap[];
  profile: VolumeProfile;
  summary: string;
}

export type PivotStrength = 3 | 5 | 10 | 20;

export interface AnalyzeOptions {
  pivotStrength?: PivotStrength;
  includeHigherTimeframes?: boolean;
}
