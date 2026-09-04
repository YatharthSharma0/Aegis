import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { ApiError } from "../api/client";
import { startTrace } from "../api/trace";
import type { Chain, TaintModel, TraceRequest } from "../api/types";
import { Button } from "../ui/Button";
import { Card } from "../ui/Card";
import { Field } from "../ui/Field";
import { textInputClass } from "../ui/inputClass";

const CHAINS: Chain[] = [
  "tron",
  "ethereum",
  "bitcoin",
  "bnb",
  "polygon",
  "solana",
];
const TAINT_MODELS: TaintModel[] = ["haircut", "poison"];

export function NewTracePage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const caseId = params.get("case");

  const [address, setAddress] = useState("");
  const [chain, setChain] = useState<Chain>("tron");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [maxHops, setMaxHops] = useState(8);
  const [minTaint, setMinTaint] = useState("0.01");
  const [minValue, setMinValue] = useState("10");
  const [taintModel, setTaintModel] = useState<TaintModel>("haircut");

  const run = useMutation({
    mutationFn: (body: TraceRequest) => startTrace(body),
    onSuccess: (res) => navigate(`/trace/${res.trace_id}`),
  });

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    run.mutate({
      address: address.trim(),
      chain,
      case_id: caseId,
      params: {
        max_hops: maxHops,
        min_taint: minTaint,
        min_value: minValue,
        taint_model: taintModel,
      },
    });
  };

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <header>
        <h1 className="text-xl font-bold tracking-tight text-primary">New trace</h1>
        <p className="text-sm text-muted">
          Enter the victim-reported address to trace the fund flow and attribute
          the receiving exchange.
        </p>
      </header>

      {caseId && (
        <p className="rounded-sm border border-subtle bg-raised px-3 py-2 text-xs text-muted">
          Linked to case <span className="text-secondary">{caseId}</span>
        </p>
      )}

      <Card>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Address under investigation" htmlFor="address">
            <input
              id="address"
              required
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              placeholder="T… (Tron) / 0x… (EVM)"
              className={textInputClass("font-mono")}
              autoComplete="off"
              spellCheck={false}
            />
          </Field>

          <Field label="Chain" htmlFor="chain">
            <select
              id="chain"
              value={chain}
              onChange={(e) => setChain(e.target.value as Chain)}
              className={textInputClass()}
            >
              {CHAINS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </Field>

          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            aria-expanded={showAdvanced}
            className="text-xs text-link hover:underline"
          >
            {showAdvanced ? "Hide" : "Show"} advanced parameters
          </button>

          {showAdvanced && (
            <div className="grid gap-3 sm:grid-cols-2">
              <Field label="Max hops" htmlFor="max_hops">
                <input
                  id="max_hops"
                  type="number"
                  min={1}
                  max={64}
                  value={maxHops}
                  onChange={(e) => setMaxHops(Number(e.target.value))}
                  className={textInputClass()}
                />
              </Field>
              <Field label="Taint model" htmlFor="taint_model">
                <select
                  id="taint_model"
                  value={taintModel}
                  onChange={(e) =>
                    setTaintModel(e.target.value as TaintModel)
                  }
                  className={textInputClass()}
                >
                  {TAINT_MODELS.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              </Field>
              <Field
                label="Min taint (0–1)"
                htmlFor="min_taint"
                hint="Ignore flows below this retained-taint fraction"
              >
                <input
                  id="min_taint"
                  value={minTaint}
                  onChange={(e) => setMinTaint(e.target.value)}
                  className={textInputClass("font-mono")}
                  inputMode="decimal"
                />
              </Field>
              <Field
                label="Min value"
                htmlFor="min_value"
                hint="Ignore transfers below this amount"
              >
                <input
                  id="min_value"
                  value={minValue}
                  onChange={(e) => setMinValue(e.target.value)}
                  className={textInputClass("font-mono")}
                  inputMode="decimal"
                />
              </Field>
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button type="submit" loading={run.isPending} disabled={!address.trim()}>
              Start trace
            </Button>
            {run.isError && (
              <span className="text-sm text-risk-high" role="alert">
                {run.error instanceof ApiError
                  ? run.error.message
                  : "Could not start the trace."}
              </span>
            )}
          </div>
        </form>
      </Card>
    </div>
  );
}
