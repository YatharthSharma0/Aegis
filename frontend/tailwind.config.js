/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        navy: {
          600: "var(--navy-600)",
          700: "var(--navy-700)",
          800: "var(--navy-800)",
          900: "var(--navy-900)",
        },
        indigo: {
          300: "var(--indigo-300)",
          500: "var(--indigo-500)",
        },
        paper: "var(--paper)",
        ink: "var(--ink)",
        mute: "var(--mute)",
        risk: {
          low: "var(--risk-low)",
          med: "var(--risk-med)",
          high: "var(--risk-high)",
        },
        vasp: "var(--vasp)",
        confirmed: "var(--confirmed)",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'Menlo', 'Consolas', 'monospace'],
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        sm: "var(--radius-sm)",
      },
    },
  },
  plugins: [],
};
