import { CircleX, Focus, GitBranch, LayoutGrid } from "lucide-react";

import { cn } from "../ui/cn";

const toggleBtn = (active: boolean) =>
  cn(
    "inline-flex items-center gap-1.5 rounded-sm border px-2 py-1 text-xs transition-colors duration-fast",
    active
      ? "border-brand bg-hover text-primary"
      : "border-subtle text-secondary hover:bg-hover hover:text-primary",
  );

/** Controls for the money-flow graph: layout, path isolation, and a value filter. */
export function GraphToolbar({
  layout,
  onLayoutChange,
  isolate,
  onIsolateChange,
  minValue,
  onMinValueChange,
  onClearSelection,
  hasSelection,
}: {
  layout: "dagre" | "grid";
  onLayoutChange: (layout: "dagre" | "grid") => void;
  isolate: boolean;
  onIsolateChange: (isolate: boolean) => void;
  minValue: number;
  onMinValueChange: (value: number) => void;
  onClearSelection: () => void;
  hasSelection: boolean;
}) {
  return (
    <div
      className="mb-2 flex flex-wrap items-center gap-3 border-b border-subtle pb-2"
      aria-label="Graph controls"
    >
      <div className="flex gap-1">
        <button
          type="button"
          className={toggleBtn(layout === "dagre")}
          onClick={() => onLayoutChange("dagre")}
          title="Directed hop layout"
        >
          <GitBranch size={14} aria-hidden />
          Hop
        </button>
        <button
          type="button"
          className={toggleBtn(layout === "grid")}
          onClick={() => onLayoutChange("grid")}
          title="Compact grid layout"
        >
          <LayoutGrid size={14} aria-hidden />
          Grid
        </button>
      </div>

      <div className="flex gap-1">
        <button
          type="button"
          className={toggleBtn(isolate)}
          onClick={() => onIsolateChange(!isolate)}
          disabled={!hasSelection}
          title="Fade everything except the path to the selected node"
        >
          <Focus size={14} aria-hidden />
          Isolate path
        </button>
        <button
          type="button"
          className={toggleBtn(false)}
          onClick={onClearSelection}
          disabled={!hasSelection}
          title="Clear node selection"
        >
          <CircleX size={14} aria-hidden />
          Clear
        </button>
      </div>

      <label className="ml-auto flex items-center gap-1.5 text-xs text-muted">
        Min value
        <select
          value={minValue}
          onChange={(e) => onMinValueChange(Number(e.target.value))}
          className="rounded-sm border border-subtle bg-base px-1.5 py-1 text-xs text-secondary"
        >
          <option value="0">All</option>
          <option value="100">100+</option>
          <option value="1000">1,000+</option>
          <option value="5000">5,000+</option>
        </select>
      </label>
    </div>
  );
}
