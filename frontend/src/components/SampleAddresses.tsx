import { useEffect, useState } from "react";

import type { Scenario } from "../demo/scenarios";
import { Card } from "../ui/Card";

/** The addresses demo mode can trace. The data loads lazily, so live builds skip it. */
export function SampleAddresses({ onSelect }: { onSelect: (address: string) => void }) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);

  useEffect(() => {
    let active = true;
    void import("../demo/scenarios").then((m) => {
      if (active) setScenarios(m.SCENARIOS);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <Card title="Sample addresses">
      <p className="mb-2 text-xs text-muted">
        Pick one, then start the trace. Advanced parameters do not change a
        recorded sample result.
      </p>
      <ul className="divide-y divide-subtle">
        {scenarios.map((s) => (
          <li key={s.key}>
            <button
              type="button"
              onClick={() => onSelect(s.seed)}
              className="w-full py-2 text-left transition-colors duration-fast hover:bg-hover"
            >
              <span className="block text-sm font-medium text-primary">{s.title}</span>
              <span className="block text-xs text-muted">{s.description}</span>
              <span className="block break-all font-mono text-xs text-secondary">
                {s.seed}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </Card>
  );
}
