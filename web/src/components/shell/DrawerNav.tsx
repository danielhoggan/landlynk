"use client";

import { useEffect } from "react";
import { Map, FileText, Settings, X, History } from "lucide-react";

interface NavItem {
  label: string;
  icon: React.ComponentType<{ size?: number }>;
  href: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Catchment map", icon: Map, href: "/" },
  { label: "Battlecards", icon: FileText, href: "/battlecards" },
  { label: "History", icon: History, href: "/history" },
  { label: "Settings", icon: Settings, href: "/settings" },
];

interface DrawerNavProps {
  open: boolean;
  onClose: () => void;
}

// Slide-out drawer navigation with a blurred scrim and scroll lock when open
// (design-framework.md, layout shell).
export function DrawerNav({ open, onClose }: DrawerNavProps) {
  useEffect(() => {
    // Scroll lock while the drawer is open.
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
      {/* Blurred scrim */}
      <div
        aria-hidden={!open}
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/30 frosted transition-opacity duration-300 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <nav
        aria-label="Main navigation"
        className={`fixed left-0 top-0 z-50 h-full w-72 max-w-[80%] border-r border-neutral-200 bg-white/95 p-5 frosted transition-transform duration-[280ms] ease-drawer dark:border-neutral-800 dark:bg-black/90 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-center justify-between">
          <span className="text-lg font-semibold">landlynk</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100"
          >
            <X size={22} />
          </button>
        </div>
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <li key={item.href}>
                <a
                  href={item.href}
                  className="flex items-center gap-3 rounded-card px-3 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-100 hover:text-light-accent dark:text-neutral-200 dark:hover:bg-neutral-900 dark:hover:text-dark-accent"
                >
                  <Icon size={18} />
                  {item.label}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>
    </>
  );
}
