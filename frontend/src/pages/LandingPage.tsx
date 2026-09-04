import { ArrowRight, FileSearch, Link2, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { useTheme } from "../app/theme";
import { Radar } from "../components/Radar";
import { ThemeToggle } from "../components/ThemeToggle";

// Radar is WebGL — it can't read CSS custom properties, so these are kept
// in sync with tokens.css by hand (same pattern as GraphCanvas.tsx).
const RADAR_BY_THEME = {
  night: { color: "#57c68f", backgroundColor: "#071013", lightMode: false, brightness: 1.0 },
  day: { color: "#1a6fd6", backgroundColor: "#ffffff", lightMode: true, brightness: 1.25 },
} as const;

const STEPS = [
  {
    icon: Link2,
    title: "Report a wallet",
    body: "An officer enters the victim-reported crypto address from an NCRP / 1930 complaint.",
  },
  {
    icon: FileSearch,
    title: "Trace the fund flow",
    body: "A deterministic forward walk follows the money hop by hop, propagating a haircut taint through every split.",
  },
  {
    icon: ShieldCheck,
    title: "Attribute, with evidence",
    body: "A two-tier match — dataset-confirmed or heuristic — surfaces the receiving exchange with a transparent confidence score.",
  },
];

export function LandingPage() {
  const theme = useTheme();
  const radar = RADAR_BY_THEME[theme];

  return (
    <div className="min-h-screen bg-canvas text-primary">
      <header className="relative z-10 flex h-16 items-center gap-6 px-4 sm:px-8">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center border-2 border-brand text-xs font-semibold text-brand">
            Æ
          </span>
          <span className="text-base font-semibold tracking-tight">Aegis</span>
        </div>

        <nav className="hidden flex-1 items-center justify-center gap-8 text-xs uppercase tracking-widest text-secondary sm:flex">
          <a href="#how-it-works" className="hover:text-primary">
            How it works
          </a>
          <a href="#evidence" className="hover:text-primary">
            Evidence
          </a>
        </nav>

        <div className="ml-auto flex items-center gap-3">
          <ThemeToggle />
          <Link
            to="/login"
            className="rounded-sm bg-brand px-4 py-2 text-xs font-semibold uppercase tracking-wide text-ink hover:bg-brand-hover"
          >
            Officer sign-in
          </Link>
        </div>
      </header>

      <section className="relative flex min-h-[calc(100vh-4rem)] items-center justify-center overflow-hidden">
        <div className="absolute inset-0">
          <Radar
            speed={0.9}
            scale={0.55}
            ringCount={10}
            spokeCount={12}
            sweepSpeed={0.6}
            sweepWidth={2.5}
            color={radar.color}
            backgroundColor={radar.backgroundColor}
            brightness={radar.brightness}
            lightMode={radar.lightMode}
            enableMouseInteraction
            mouseInfluence={0.08}
          />
        </div>

        <div className="relative z-10 mx-auto max-w-2xl px-4 text-center">
          <p className="text-xs uppercase tracking-[0.3em] text-muted">
            SIH26183 · Ministry of Home Affairs · I4C
          </p>
          <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Follow the Money, On-Chain
          </h1>
          <p className="mx-auto mt-5 max-w-md text-xs uppercase tracking-[0.2em] text-secondary">
            Trace a reported wallet to the exchange that cashed it out
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 rounded-sm bg-brand px-5 py-2.5 text-sm font-medium text-ink hover:bg-brand-hover"
            >
              Officer sign-in
              <ArrowRight size={15} aria-hidden />
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex items-center gap-1.5 rounded-sm border border-strong px-5 py-2.5 text-sm font-medium text-secondary hover:bg-hover hover:text-primary"
            >
              How it works
            </a>
          </div>
        </div>
      </section>

      <section
        id="how-it-works"
        className="mx-auto max-w-5xl px-4 py-16 sm:px-8"
      >
        <h2 className="text-center text-xl font-bold tracking-tight">
          A lead, not a verdict
        </h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-sm text-muted">
          Aegis reads public blockchain data and reports. It never signs a
          transaction, holds funds, or acts on its own — an officer reviews
          every attribution before any lawful request goes out.
        </p>

        <div className="mt-10 grid gap-6 sm:grid-cols-3">
          {STEPS.map((step, i) => (
            <div
              key={step.title}
              id={i === 2 ? "evidence" : undefined}
              className="rounded-sm border border-subtle bg-raised p-5"
            >
              <step.icon size={20} className="text-brand" aria-hidden />
              <h3 className="mt-3 text-sm font-semibold">{step.title}</h3>
              <p className="mt-1.5 text-sm text-muted">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-subtle px-4 py-6 text-center text-xs text-muted sm:px-8">
        Aegis · Smart India Hackathon 2026 · Read-only against public
        blockchain data — no wallets, no on-chain writes.
      </footer>
    </div>
  );
}
