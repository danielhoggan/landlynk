"use client";

import { useEffect } from "react";
import { X, LogOut } from "lucide-react";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import { Logo } from "./Logo";
import { NAV_ITEMS, isActive } from "./navItems";
import { ReferenceStatusDot } from "./ReferenceStatusDot";
import { useUser } from "@/lib/userContext";

interface DrawerNavProps {
  open: boolean;
  onClose: () => void;
}

// Mobile navigation: a slide-out drawer with a blurred scrim and scroll lock.
// Desktop uses the persistent Sidebar instead.
export function DrawerNav({ open, onClose }: DrawerNavProps) {
  const pathname = usePathname();
  const { isAdmin } = useUser();
  const mainItems = NAV_ITEMS.filter((i) => !i.adminOnly);
  const adminItems = isAdmin ? NAV_ITEMS.filter((i) => i.adminOnly) : [];

  const renderItem = (item: (typeof NAV_ITEMS)[number]) => {
    const Icon = item.icon;
    const active = isActive(pathname, item.href);
    return (
      <li key={item.href}>
        <a
          href={item.href}
          onClick={onClose}
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

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  return (
    <div className="md:hidden">
      <div
        aria-hidden={!open}
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/30 frosted transition-opacity duration-300 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <nav
        aria-label="Main navigation"
        className={`fixed left-0 top-0 z-50 flex h-full w-72 max-w-[80%] flex-col border-r border-neutral-200 bg-white p-5 transition-transform duration-[280ms] ease-drawer ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-8 flex items-center justify-between">
          <Logo className="text-lg" />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="text-neutral-500 hover:text-neutral-900"
          >
            <X size={22} />
          </button>
        </div>
        <ul className="space-y-1">{mainItems.map(renderItem)}</ul>
        {adminItems.length > 0 && (
          <>
            <p className="mb-1 mt-5 px-3 text-xs font-semibold uppercase tracking-wider text-neutral-400">
              Admin
            </p>
            <ul className="space-y-1">{adminItems.map(renderItem)}</ul>
          </>
        )}
        <div className="mt-auto space-y-3">
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
              LandLynk. The Geographic Intelligence Engine. Open data,
              explainable rankings.
            </p>
          </div>
        </div>
      </nav>
    </div>
  );
}
