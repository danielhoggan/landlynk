"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "./ThemeProvider";

// Persistent light and dark mode toggle, bottom-left, position fixed
// (design-framework.md, theme toggle).
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="fixed bottom-4 left-4 z-50 flex h-11 w-11 items-center justify-center rounded-card border border-neutral-300 bg-white/80 text-neutral-700 frosted transition-colors hover:text-light-accent dark:border-neutral-700 dark:bg-black/60 dark:text-neutral-200 dark:hover:text-dark-accent"
    >
      {isDark ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  );
}
