// Tailwind cannot add an opacity to a bare var(), so utilities such as
// `border-success/40` were silently dropped. color-mix applies it.
const token = (name) =>
  `color-mix(in srgb, var(${name}) calc(<alpha-value> * 100%), transparent)`;

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: token("--bg-canvas"),
        base: token("--bg-base"),
        raised: token("--bg-raised"),
        elevated: token("--bg-elevated"),
        hover: token("--bg-hover"),
        paper: token("--paper"),
        ink: token("--ink"),
        primary: token("--text-primary"),
        secondary: token("--text-secondary"),
        muted: token("--text-muted"),
        subtle: token("--border-subtle"),
        strong: token("--border-strong"),
        brand: {
          DEFAULT: token("--brand"),
          hover: token("--brand-hover"),
        },
        link: token("--link"),
        info: token("--info"),
        success: token("--success"),
        warning: token("--warning"),
        risk: {
          high: token("--risk-high"),
          critical: token("--risk-critical"),
        },
        unknown: token("--unknown"),
        entity: {
          vasp: token("--entity-vasp"),
          contract: token("--entity-contract"),
          bridge: token("--entity-bridge"),
          cluster: token("--entity-cluster"),
        },
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', "system-ui", '"Segoe UI"', "Roboto", "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "Menlo", "Consolas", "monospace"],
      },
      borderRadius: {
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        DEFAULT: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      transitionDuration: {
        instant: "var(--duration-instant)",
        fast: "var(--duration-fast)",
        base: "var(--duration-base)",
        slow: "var(--duration-slow)",
      },
      transitionTimingFunction: {
        standard: "var(--ease-standard)",
        enter: "var(--ease-enter)",
        exit: "var(--ease-exit)",
      },
    },
  },
  plugins: [],
};
