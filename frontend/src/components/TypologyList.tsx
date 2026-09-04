import type { TypologyOut } from "../api/types";
import { Mono } from "../ui/Mono";

/** Detected laundering typologies with their model and score. */
export function TypologyList({ typologies }: { typologies: TypologyOut[] }) {
  if (typologies.length === 0) {
    return <p className="text-sm text-mute">No laundering typologies detected.</p>;
  }
  return (
    <ul className="space-y-3">
      {typologies.map((t, i) => {
        const score = Math.min(1, Math.max(0, Number(t.score)));
        return (
          <li key={`${t.name}-${i}`}>
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium text-slate-200">{t.name}</span>
              <span className="text-xs text-mute">
                {t.model} · {(score * 100).toFixed(0)}%
              </span>
            </div>
            <div
              className="mt-1 h-1.5 overflow-hidden rounded-full bg-navy-700"
              role="meter"
              aria-valuenow={Math.round(score * 100)}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${t.name} score`}
            >
              <span
                className="block h-full bg-risk-med"
                style={{ width: `${score * 100}%` }}
              />
            </div>
            {t.addresses.length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5">
                {t.addresses.slice(0, 6).map((a) => (
                  <Mono key={a} value={a} />
                ))}
                {t.addresses.length > 6 && (
                  <span className="text-xs text-mute">
                    +{t.addresses.length - 6} more
                  </span>
                )}
              </div>
            )}
          </li>
        );
      })}
    </ul>
  );
}
