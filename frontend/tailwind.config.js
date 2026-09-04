/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--bg-canvas)",
        base: "var(--bg-base)",
        raised: "var(--bg-raised)",
        elevated: "var(--bg-elevated)",
        hover: "var(--bg-hover)",
        paper: "var(--paper)",
        ink: "var(--ink)",
        primary: "var(--text-primary)",
        secondary: "var(--text-secondary)",
        muted: "var(--text-muted)",
        subtle: "var(--border-subtle)",
        strong: "var(--border-strong)",
        brand: {
          DEFAULT: "var(--brand)",
          hover: "var(--brand-hover)",
        },
        link: "var(--link)",
        info: "var(--info)",
        success: "var(--success)",
        warning: "var(--warning)",
        risk: {
          high: "var(--risk-high)",
          critical: "var(--risk-critical)",
        },
        unknown: "var(--unknown)",
        entity: {
          vasp: "var(--entity-vasp)",
          contract: "var(--entity-contract)",
          bridge: "var(--entity-bridge)",
          cluster: "var(--entity-cluster)",
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
