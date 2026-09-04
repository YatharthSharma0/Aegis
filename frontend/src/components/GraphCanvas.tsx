import cytoscape from "cytoscape";
import dagre from "cytoscape-dagre";
import { useEffect, useMemo, useRef } from "react";

import type { GraphEdgeOut, GraphNodeOut } from "../api/types";
import { Mono } from "../ui/Mono";

let registered = false;
function ensureDagre() {
  if (!registered) {
    cytoscape.use(dagre);
    registered = true;
  }
}

const RISK_COLOURS = {
  low: "#2e7d32",
  med: "#e08600",
  high: "#c62828",
  unknown: "#5b6472",
};

function riskColour(risk: string | null): string {
  if (risk === null) return RISK_COLOURS.unknown;
  const v = Number(risk);
  if (!Number.isFinite(v)) return RISK_COLOURS.unknown;
  if (v >= 0.66) return RISK_COLOURS.high;
  if (v >= 0.33) return RISK_COLOURS.med;
  return RISK_COLOURS.low;
}

const SHAPE_BY_KIND: Record<string, cytoscape.Css.NodeShape> = {
  seed: "diamond",
  vasp: "round-rectangle",
  exchange: "round-rectangle",
  mixer: "triangle",
  bridge: "hexagon",
};

function shortId(id: string) {
  return id.length > 14 ? `${id.slice(0, 6)}…${id.slice(-4)}` : id;
}

/**
 * Money-flow graph. Cytoscape draws the picture; the `<details>` table below
 * is the keyboard/screen-reader equivalent (Style Guide: the graph is never
 * the only way to read the evidence).
 */
export function GraphCanvas({
  nodes,
  edges,
}: {
  nodes: GraphNodeOut[];
  edges: GraphEdgeOut[];
}) {
  const boxRef = useRef<HTMLDivElement | null>(null);

  const elements = useMemo(
    () => [
      ...nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.vasp_name ?? shortId(n.id),
          colour: riskColour(n.risk),
          shape: SHAPE_BY_KIND[n.kind] ?? "ellipse",
          verified: n.verified ? 1 : 0,
        },
      })),
      ...edges.map((e, i) => ({
        data: {
          id: `e${i}`,
          source: e.from,
          target: e.to,
          label: `${e.value} ${e.asset}`,
        },
      })),
    ],
    [nodes, edges],
  );

  useEffect(() => {
    if (!boxRef.current) return;
    ensureDagre();
    const cy = cytoscape({
      container: boxRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": "data(colour)",
            shape: "data(shape)" as cytoscape.Css.PropertyValueNode<cytoscape.Css.NodeShape>,
            label: "data(label)",
            color: "#e7ecf5",
            "font-size": 10,
            "font-family": "JetBrains Mono, monospace",
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: 26,
            height: 26,
            "border-width": "data(verified)",
            "border-color": "#0e7c86",
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#3a4a67",
            "target-arrow-color": "#3a4a67",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 8,
            color: "#8592a8",
            "text-rotation": "autorotate",
          },
        },
      ],
      layout: { name: "dagre", rankDir: "LR", nodeSep: 24, rankSep: 60 } as cytoscape.LayoutOptions,
      minZoom: 0.2,
      maxZoom: 2.5,
    });
    cy.fit(undefined, 24);
    return () => cy.destroy();
  }, [elements]);

  return (
    <div>
      <div
        ref={boxRef}
        className="h-[420px] w-full rounded border border-navy-700 bg-navy-900"
        role="img"
        aria-label={`Money-flow graph: ${nodes.length} addresses, ${edges.length} transfers`}
      />
      <div className="mt-2 flex flex-wrap gap-3 text-xs text-mute">
        <Legend colour={RISK_COLOURS.high} label="High risk" />
        <Legend colour={RISK_COLOURS.med} label="Medium risk" />
        <Legend colour={RISK_COLOURS.low} label="Low risk" />
        <Legend colour={RISK_COLOURS.unknown} label="Unknown" />
        <span>◇ seed · ▭ VASP · △ mixer · ⬡ bridge</span>
      </div>

      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-mute hover:text-slate-300">
          Transfers as a table ({edges.length})
        </summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="text-mute">
              <tr className="border-b border-navy-700 text-left">
                <th className="py-1 pr-3">From</th>
                <th className="py-1 pr-3">To</th>
                <th className="py-1 pr-3">Value</th>
                <th className="py-1 pr-3">Taint</th>
                <th className="py-1">Tx</th>
              </tr>
            </thead>
            <tbody>
              {edges.map((e, i) => (
                <tr key={i} className="border-b border-navy-800">
                  <td className="py-1 pr-3">
                    <Mono value={e.from} />
                  </td>
                  <td className="py-1 pr-3">
                    <Mono value={e.to} />
                  </td>
                  <td className="py-1 pr-3">
                    {e.value} {e.asset}
                  </td>
                  <td className="py-1 pr-3">{Number(e.taint).toFixed(3)}</td>
                  <td className="py-1">
                    <Mono value={e.tx_hash} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

function Legend({ colour, label }: { colour: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1">
      <span
        className="h-2.5 w-2.5 rounded-full"
        style={{ backgroundColor: colour }}
        aria-hidden
      />
      {label}
    </span>
  );
}
