"use client";

import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import { LogOut } from "lucide-react";
import { Logo } from "./Logo";
import { navSections, isActive } from "./navItems";
import { ReferenceStatusDot } from "./ReferenceStatusDot";
import { AllowanceBadge } from "./AllowanceBadge";
import { BrandSelector } from "./BrandSelector";
import { useUser } from "@/lib/userContext";

// Persistent, fixed sidebar for desktop. Hidden on mobile, where the burger
// drawer is used instead.
export function Sidebar() {
  const pathname = usePathname();
  const { isAdmin } = useUser();
  const sections = navSections(isAdmin);

  const renderItem = (item: ReturnType<typeof navSections>[number]["items"][number]) => {
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
  };

  return (
    <aside className="fixed left-0 top-0 z-30 hidden h-full w-60 flex-col border-r border-neutral-200 bg-white px-4 py-5 md:flex">
      <a href="/" className="mb-4 px-2">
        <Logo className="text-lg" />
      </a>
      <div className="mb-6">
        <BrandSelector />
      </div>
      <nav aria-label="Main navigation">
        {sections.map((section, i) => (
          <div key={section.id}>
            <p
              className={`mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-neutral-400 ${
                i === 0 ? "" : "mt-5"
              }`}
            >
              {section.heading}
            </p>
            <ul className="space-y-1">{section.items.map(renderItem)}</ul>
          </div>
        ))}
      </nav>
      <div className="mt-auto space-y-3">
        <AllowanceBadge />
        <ReferenceStatusDot />
        <button
          type="button"
          onClick={() => signOut({ callbackUrl: "/signin" })}
          className="flex w-full items-center gap-3 rounded-card px-3 py-2.5 text-sm font-medium text-neutral-700 transition-colors hover:bg-neutral-100"
        >
          <LogOut size={18} /> Sign out
        </button>
        <div className="border-t border-neutral-200 px-2 pt-3">
          <p className="text-xs font-medium text-neutral-500">
            Product of Mediaworks
          </p>
          <p className="mt-1 text-xs text-neutral-400">
            LandLynk. The Geographic Intelligence Engine. Open data, explainable
            rankings.
          </p>
        </div>
      </div>
    </aside>
  );
}
