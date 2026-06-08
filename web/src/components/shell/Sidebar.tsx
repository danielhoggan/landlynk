"use client";

import { usePathname } from "next/navigation";
import { Logo } from "./Logo";
import { NAV_ITEMS, isActive } from "./navItems";

// Persistent, fixed sidebar for desktop. Hidden on mobile, where the burger
// drawer is used instead.
export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed left-0 top-0 z-30 hidden h-full w-60 flex-col border-r border-neutral-200 bg-white px-4 py-5 md:flex">
      <a href="/" className="mb-8 px-2">
        <Logo className="text-lg" />
      </a>
      <nav aria-label="Main navigation">
        <ul className="space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(pathname, item.href);
            return (
              <li key={item.href}>
                <a
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-3 rounded-card px-3 py-2.5 text-sm font-medium transition-colors ${
                    active
                      ? "bg-light-accent/10 text-light-accent"
                      : "text-neutral-700 hover:bg-neutral-100"
                  }`}
                >
                  <Icon size={18} />
                  {item.label}
                </a>
              </li>
            );
          })}
        </ul>
      </nav>
      <p className="mt-auto px-2 text-xs text-neutral-400">
        The Geographic Intelligence Engine. Open data, explainable rankings.
      </p>
    </aside>
  );
}
