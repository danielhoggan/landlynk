"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { TopBar } from "./TopBar";
import { DrawerNav } from "./DrawerNav";
import { Sidebar } from "./Sidebar";
import { MobileTabBar } from "./MobileTabBar";
import { ReferenceWarning } from "./ReferenceWarning";
import { BrandTheme } from "./BrandTheme";

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
      <BrandTheme />
      <Sidebar />
      <DrawerNav open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <div className="md:pl-60">
        <TopBar onOpenDrawer={() => setDrawerOpen(true)} />
        <ReferenceWarning />
        {/* Pad the bottom on mobile so content clears the fixed tab bar. */}
        <main className="pb-20 md:pb-0">{children}</main>
      </div>
      <MobileTabBar />
    </div>
  );
}
