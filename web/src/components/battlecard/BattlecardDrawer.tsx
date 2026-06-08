"use client";

import { useEffect } from "react";
import { X, Download } from "lucide-react";
import type { Battlecard } from "@/lib/types/battlecard";
import { OnLocationSummary } from "./OnLocationSummary";
import { ScoreExplainer } from "./ScoreExplainer";
import { BattlecardCharts } from "./BattlecardCharts";
import { BattlecardInsights } from "./BattlecardInsights";

interface BattlecardDrawerProps {
  battlecard: Battlecard | null;
  open: boolean;
  onClose: () => void;
  /** Download URL for the PDF export, when a catchment is loaded. */
  pdfUrl?: string;
}

// Clicking a region opens its deep-dive in the slide-out drawer, never a full
// page navigation, so the map stays in view (design-framework.md, the map). The
// drawer is focus-managed. Battlecard prose uses the web output font.
export function BattlecardDrawer({
  battlecard,
  open,
  onClose,
  pdfUrl,
}: BattlecardDrawerProps) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Area Battlecard"
      aria-hidden={!open}
      className={`fixed right-0 top-0 z-50 h-full w-full max-w-md overflow-y-auto border-l border-neutral-200 bg-white p-5 shadow-none transition-transform duration-[280ms] ease-drawer dark:border-neutral-800 dark:bg-neutral-950 ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      <div className="mb-4 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close Battlecard"
          className="text-neutral-500 hover:text-neutral-900 dark:hover:text-neutral-100"
        >
          <X size={22} />
        </button>
      </div>

      {battlecard ? (
        <div className="space-y-6">
          <OnLocationSummary battlecard={battlecard} onOpenFull={() => {}} />

          {pdfUrl && (
            <a
              href={pdfUrl}
              className="flex items-center justify-center gap-2 rounded-card border border-neutral-300 py-2 text-sm font-semibold dark:border-neutral-700"
            >
              <Download size={16} /> Export PDF Battlecard
            </a>
          )}

          <BattlecardInsights
            pricing={battlecard.pricingRationale}
            segments={battlecard.addressableSegments}
            context={battlecard.catchmentContext}
            confidence={battlecard.dataConfidence}
          />

          <BattlecardCharts charts={battlecard.visualSummary.charts} />

          <ScoreExplainer score={battlecard.score} />

          {/* Page 2 and 3 commentary. Output font, signal-driven prose. */}
          <section className="output-prose space-y-4 text-sm leading-relaxed">
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-400">
                Household income
              </p>
              <p>{battlecard.incomeAndTenure.incomeCommentary}</p>
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-neutral-400">
                Housing tenure
              </p>
              <p>{battlecard.incomeAndTenure.tenureCommentary}</p>
            </div>
          </section>
        </div>
      ) : (
        <p className="text-sm text-neutral-500">Select an area to see its Battlecard.</p>
      )}
    </div>
  );
}
