"use client";

import { useEffect } from "react";
import {
  Map,
  Compass,
  Database,
  Settings,
  X,
  History,
  type LucideIcon,
} from "lucide-react";
import { usePathname } from "next/navigation";
import { Logo } from "./Logo";

interface NavItem {
  label: string;
  icon: LucideIcon;
  href: string;
}

// The standard nav. Battlecards are reached by clicking an area inside a
// catchment, so they are not a top-level destination.
const NAV_ITEMS: NavItem[] = [
  { label: "Catchment map", icon: Map, href: "/" },
  { label: "How it works", icon: Compass, href: "/how-it-works" },
  { label: "History", icon: History, href: "/history" },
  { label: "Reference data", icon: Database, href: "/data" },
  { label: "Settings", icon: Settings, href: "/settings" },
];

interface DrawerNavProps {
  open: boolean;
  onClose: () => void;
}

// Slide-out drawer navigation with a blurred scrim and scroll lock when open
// (design-framework.md, layout shell).
export function DrawerNav({ open, onClose }: DrawerNavProps) {
  const pathname = usePathname();

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <>
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
          <Logo className="text-lg" />
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
            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);
            return (
              <li key={item.href}>
                <a
                  href={item.href}
                  onClick={onClose}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-3 rounded-card px-3 py-2.5 text-sm font-medium transition-colors ${
                    active
                      ? "bg-light-accent/10 text-light-accent dark:bg-dark-accent/15 dark:text-dark-accent"
                      : "text-neutral-700 hover:bg-neutral-100 dark:text-neutral-200 dark:hover:bg-neutral-900"
                  }`}
                >
                  <Icon size={18} />
                  {item.label}
                </a>
              </li>
            );
          })}
        </ul>

        <p className="absolute bottom-5 left-5 right-5 text-xs text-neutral-400">
          The Geographic Intelligence Engine. Open data, explainable rankings.
        </p>
      </nav>
    </>
  );
}
