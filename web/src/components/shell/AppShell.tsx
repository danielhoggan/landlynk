"use client";

import { useState } from "react";
import { TopBar } from "./TopBar";
import { DrawerNav } from "./DrawerNav";
import { Sidebar } from "./Sidebar";

// Light, Apple-style shell. A fixed sidebar on desktop, a burger drawer on
// mobile. Content is offset to clear the sidebar on desktop.
export function AppShell({ children }: { children: React.ReactNode }) {
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <div className="min-h-screen">
      <Sidebar />
      <DrawerNav open={drawerOpen} onClose={() => setDrawerOpen(false)} />
      <div className="md:pl-60">
        <TopBar onOpenDrawer={() => setDrawerOpen(true)} />
        <main>{children}</main>
      </div>
    </div>
  );
}
