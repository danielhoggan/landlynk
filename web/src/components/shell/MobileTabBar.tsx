"use client";

import { usePathname } from "next/navigation";
import { Map, History, Archive, Settings, type LucideIcon } from "lucide-react";
import { isActive } from "./navItems";

// Fixed bottom tab bar for mobile: quick access to the primary catchment
// actions, complementing the burger drawer (which still carries the full nav,
// including Info and Admin). Hidden on desktop, where the sidebar is used.
const TABS: { label: string; icon: LucideIcon; href: string }[] = [
  { label: "New", icon: Map, href: "/" },
  { label: "Previous", icon: History, href: "/history" },
  { label: "Archived", icon: Archive, href: "/archived" },
  { label: "Settings", icon: Settings, href: "/settings" },
];

export function MobileTabBar() {
  const pathname = usePathname();
  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-0 z-40 flex border-t border-neutral-200 bg-white/90 frosted md:hidden"
    >
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const active = isActive(pathname, tab.href);
        return (
          <a
            key={tab.href}
            href={tab.href}
            aria-current={active ? "page" : undefined}
            className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] font-medium transition-colors ${
              active ? "text-light-accent" : "text-neutral-500"
            }`}
          >
            <Icon size={20} />
            {tab.label}
          </a>
        );
      })}
    </nav>
  );
}
