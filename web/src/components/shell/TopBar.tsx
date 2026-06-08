"use client";

import { Menu } from "lucide-react";
import { Logo } from "./Logo";

interface TopBarProps {
  onOpenDrawer: () => void;
}

// Mobile-only top bar with the burger and logo. Hidden on desktop, where the
// persistent sidebar carries the logo and navigation.
export function TopBar({ onOpenDrawer }: TopBarProps) {
  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-neutral-200 bg-white/70 px-4 frosted md:hidden">
      <button
        type="button"
        onClick={onOpenDrawer}
        aria-label="Open menu"
        className="text-neutral-700 transition-colors hover:text-light-accent"
      >
        <Menu size={22} />
      </button>
      <Logo className="text-base" />
    </header>
  );
}
