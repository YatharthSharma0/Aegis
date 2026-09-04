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

// Kept in sync with src/styles/tokens.css — Cytoscape styles can't read CSS
// custom properties, so the hex values are duplicated here.
const TOKEN = {
  textPrimary: "#e7eff0",
  textMuted: "#72858a",
  borderSubtle: "#23343a",
  brand: "#c8a96a",
  unknown: "#839297",
  warning: "#d1a650",
  riskHigh: "#e0795e",
  riskCritical: "#f05b61",
  entityVasp: "#5fb7a7",
  entityContract: "#7896c7",
  entityBridge: "#a48bc3",
  entityCluster: "#60767d",
};

/** Risk bands per the blueprint: 0-29 low, 30-59 elevated, 60-79 high, 80-100
 * critical. Low reads as neutral (not "success") — risk color is reserved
 * for actual concern. */
function riskBand(risk: string | null): { colour: string; label: string } {
  if (risk === null) return { colour: TOKEN.unknown, label: "Not scored" };
  const v = Number(risk);
  if (!Number.isFinite(v)) return { colour: TOKEN.unknown, label: "Not scored" };
  if (v >= 0.8) return { colour: TOKEN.riskCritical, label: "Critical" };
  if (v >= 0.6) return { colour: TOKEN.riskHigh, label: "High" };
  if (v >= 0.3) return { colour: TOKEN.warning, label: "Elevated" };
  return { colour: TOKEN.unknown, label: "Low" };
}

interface EntitySpec {
  shape: cytoscape.Css.NodeShape;
  ring: string;
  size: number;
  entityLabel: string;
}

// Entity category is encoded by shape + ring colour, never by filling the
// whole node — an exchange endpoint must not read as "fraud".
const ENTITY_BY_KIND: Record<string, EntitySpec> = {
  seed: { shape: "ellipse", ring: TOKEN.brand, size: 40, entityLabel: "Reported address" },
  intermediary: { shape: "ellipse", ring: TOKEN.unknown, size: 30, entityLabel: "Unknown wallet" },
  cluster_peer: { shape: "ellipse", ring: TOKEN.entityCluster, size: 30, entityLabel: "Cluster peer" },
  vasp_deposit: { shape: "hexagon", ring: TOKEN.entityVasp, size: 36, entityLabel: "VASP deposit" },
  mixer: { shape: "octagon", ring: TOKEN.riskHigh, size: 34, entityLabel: "Mixer / service of concern" },
  bridge: { shape: "diamond", ring: TOKEN.entityBridge, size: 34, entityLabel: "Bridge" },
  sink: { shape: "ellipse", ring: TOKEN.unknown, size: 30, entityLabel: "Unattributed sink" },
};

const DEFAULT_ENTITY: EntitySpec = {
  shape: "ellipse",
  ring: TOKEN.unknown,
  size: 30,
  entityLabel: "Unknown wallet",
};

function shortId(id: string) {
  return id.length > 14 ? `${id.slice(0, 6)}…${id.slice(-4)}` : id;
}

const LEGEND_ENTITIES: EntitySpec[] = [
  ENTITY_BY_KIND.seed,
  ENTITY_BY_KIND.intermediary,
  ENTITY_BY_KIND.vasp_deposit,
  ENTITY_BY_KIND.bridge,
  ENTITY_BY_KIND.mixer,
];

const LEGEND_RISK: Array<[string, string]> = [
  ["Low / not scored", TOKEN.unknown],
  ["Elevated", TOKEN.warning],
  ["High", TOKEN.riskHigh],
  ["Critical", TOKEN.riskCritical],
];

/**
 * Money-flow graph. Cytoscape draws the picture; the `<details>` table below
 * is the keyboard/screen-reader equivalent — the graph is never the only way
 * to read the evidence. Entity category is shape + ring colour; risk is the
 * node fill + label, kept as a separate visual dimension so a VASP endpoint
 * never reads as "confirmed fraud."
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
      ...nodes.map((n) => {
        const entity = ENTITY_BY_KIND[n.kind] ?? DEFAULT_ENTITY;
        const risk = riskBand(n.risk);
        return {
          data: {
            id: n.id,
            label: n.vasp_name ?? shortId(n.id),
            fill: risk.colour,
            ring: entity.ring,
            shape: entity.shape,
            size: entity.size,
            verified: n.verified ? 1 : 0,
          },
        };
      }),
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
            "background-color": "data(fill)",
            "background-opacity": 0.28,
            shape: "data(shape)" as cytoscape.Css.PropertyValueNode<cytoscape.Css.NodeShape>,
            label: "data(label)",
            color: TOKEN.textPrimary,
            "font-size": 10,
            "font-family": "IBM Plex Mono, monospace",
            "text-valign": "bottom",
            "text-margin-y": 4,
            width: "data(size)",
            height: "data(size)",
            "border-width": 2,
            "border-color": "data(ring)",
          },
        },
        {
          // Known/confirmed entities get a solid ring; unverified/heuristic
          // ones get a dashed ring — the same "known vs inferred" grammar
          // used on VaspMatchCard.
          selector: "node[verified = 0]",
          style: { "border-style": "dashed" },
        },
        {
          selector: "node[verified = 1]",
          style: { "border-style": "solid" },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": TOKEN.borderSubtle,
            "target-arrow-color": TOKEN.borderSubtle,
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            label: "data(label)",
            "font-size": 8,
            "font-family": "IBM Plex Mono, monospace",
            color: TOKEN.textMuted,
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
        className="h-[420px] w-full rounded-sm border border-subtle bg-canvas"
        role="img"
        aria-label={`Money-flow graph: ${nodes.length} addresses, ${edges.length} transfers`}
      />
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-muted">
        {LEGEND_ENTITIES.map((spec) => (
          <span key={spec.entityLabel} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 border-2"
              style={{ borderColor: spec.ring, borderRadius: spec.shape === "ellipse" ? "999px" : 2 }}
              aria-hidden
            />
            {spec.entityLabel}
          </span>
        ))}
        <span className="text-subtle">·</span>
        {LEGEND_RISK.map(([label, colour]) => (
          <span key={label} className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: colour, opacity: 0.6 }}
              aria-hidden
            />
            {label}
          </span>
        ))}
        <span className="text-subtle">·</span>
        <span>dashed ring = heuristic / unverified</span>
      </div>

      <details className="mt-3">
        <summary className="cursor-pointer text-xs text-muted hover:text-secondary">
          Transfers as a table ({edges.length})
        </summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="text-muted">
              <tr className="border-b border-subtle text-left">
                <th className="py-1 pr-3">From</th>
                <th className="py-1 pr-3">To</th>
                <th className="py-1 pr-3">Value</th>
                <th className="py-1 pr-3">Taint</th>
                <th className="py-1">Tx</th>
              </tr>
            </thead>
            <tbody>
              {edges.map((e, i) => (
                <tr key={i} className="border-b border-subtle">
                  <td className="py-1 pr-3">
                    <Mono value={e.from} />
                  </td>
                  <td className="py-1 pr-3">
                    <Mono value={e.to} />
                  </td>
                  <td className="py-1 pr-3 font-mono tabular-nums">
                    {e.value} {e.asset}
                  </td>
                  <td className="py-1 pr-3 font-mono tabular-nums">
                    {Number(e.taint).toFixed(3)}
                  </td>
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
