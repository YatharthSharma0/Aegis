import { Moon, Sun } from "lucide-react";

import { toggleTheme, useTheme } from "../app/theme";

/** Switches between "night" (dark, default) and "day" (white, green/blue
 * accents) mode. The icon shows the mode a click will switch *to*. */
export function ThemeToggle() {
  const theme = useTheme();
  const isNight = theme === "night";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-pressed={!isNight}
      title={isNight ? "Switch to day mode" : "Switch to night mode"}
      className="flex items-center gap-1.5 rounded-sm border border-subtle px-2.5 py-1.5 text-xs text-secondary transition-colors duration-fast hover:bg-hover hover:text-primary"
    >
      {isNight ? (
        <Sun size={14} aria-hidden />
      ) : (
        <Moon size={14} aria-hidden />
      )}
      <span className="hidden sm:inline">{isNight ? "Day" : "Night"}</span>
    </button>
  );
}
