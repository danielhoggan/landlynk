"use client";

import { useState } from "react";

interface TabStripProps {
  tabs: string[];
  onChange?: (tab: string) => void;
}

// Horizontal scrollable tab strip for section navigation
// (design-framework.md, layout shell).
export function TabStrip({ tabs, onChange }: TabStripProps) {
  const [active, setActive] = useState(tabs[0]);

  return (
    <div className="no-scrollbar flex gap-2 overflow-x-auto border-b border-neutral-200 px-4 py-2">
      {tabs.map((tab) => {
        const isActive = tab === active;
        return (
          <button
            key={tab}
            type="button"
            onClick={() => {
              setActive(tab);
              onChange?.(tab);
            }}
            className={`whitespace-nowrap rounded-card px-3 py-1.5 text-sm font-medium transition-colors ${
              isActive
                ? "bg-light-accent text-white"
                : "text-neutral-600 hover:bg-neutral-100"
            }`}
          >
            {tab}
          </button>
        );
      })}
    </div>
  );
}
