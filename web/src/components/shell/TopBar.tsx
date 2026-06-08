"use client";

import { Menu, X } from "lucide-react";
import { Logo } from "./Logo";

interface TopBarProps {
  drawerOpen: boolean;
  onToggleDrawer: () => void;
}

// Sticky frosted-glass top bar. The hamburger turns to an x when the drawer is
// open (design-framework.md, layout shell).
export function TopBar({ drawerOpen, onToggleDrawer }: TopBarProps) {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-neutral-200 bg-white/70 px-4 frosted dark:border-neutral-800 dark:bg-black/50">
      <button
        type="button"
        onClick={onToggleDrawer}
        aria-label={drawerOpen ? "Close menu" : "Open menu"}
        aria-expanded={drawerOpen}
        className="text-neutral-700 transition-colors hover:text-light-accent dark:text-neutral-200 dark:hover:text-dark-accent"
      >
        {drawerOpen ? <X size={22} /> : <Menu size={22} />}
      </button>
      <Logo className="text-base" />
    </header>
  );
}
