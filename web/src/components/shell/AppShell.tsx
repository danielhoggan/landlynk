"use client";

import { useState } from "react";
import { TopBar } from "./TopBar";
import { DrawerNav } from "./DrawerNav";
import { ThemeToggle } from "./ThemeToggle";

// The Mediaworks HTML UI shell. Mobile-first. Composes the sticky top bar, the
// slide-out drawer navigation and the persistent theme toggle around the page
// content (design-framework.md, app shell).
export function AppShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <TopBar
        drawerOpen={drawerOpen}
        onToggleDrawer={() => setDrawerOpen((o) => !o)}
      />
      <DrawerNav open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <main>{children}</main>
      <ThemeToggle />
    </div>
  );
}
