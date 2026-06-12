"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { TopBar } from "./TopBar";
import { DrawerNav } from "./DrawerNav";
import { Sidebar } from "./Sidebar";
import { ReferenceWarning } from "./ReferenceWarning";

// Routes shown without the nav chrome. The sign-in page must not expose the
// navigation, so an unauthenticated visitor never sees the app structure.
const BARE_ROUTES = ["/signin"];

// Light, Apple-style shell. A fixed sidebar on desktop, a burger drawer on
// mobile. Content is offset to clear the sidebar on desktop.
export function AppShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pathname = usePathname();

  if (BARE_ROUTES.includes(pathname)) {
    return <main className="min-h-screen">{children}</main>;
  }

  return (
    <div className="min-h-screen">
      <Sidebar />
      <DrawerNav open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <div className="md:pl-60">
        <TopBar onOpenDrawer={() => setDrawerOpen(true)} />
        <ReferenceWarning />
        <main>{children}</main>
      </div>
    </div>
  );
}
