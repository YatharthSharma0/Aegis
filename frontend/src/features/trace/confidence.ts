export type ConfidenceBand = "low" | "medium" | "high";

export function confidenceBand(value: number): ConfidenceBand {
  if (value >= 0.7) return "high";
  if (value >= 0.4) return "medium";
  return "low";
}

/** Parse the engine's stringified numeric and clamp to [0, 1]. */
export function clampConfidence(raw: string | number): number {
  const v = typeof raw === "string" ? Number(raw) : raw;
  return Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : 0;
}
