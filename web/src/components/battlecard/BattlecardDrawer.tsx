"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { X, Download } from "lucide-react";
import type { Battlecard } from "@/lib/types/battlecard";
import type { GeoJsonGeometry } from "@/lib/types/catchment";
import type { DevelopmentSite } from "@/lib/client";
import { OnLocationSummary } from "./OnLocationSummary";
import { AreaMiniMap } from "./AreaMiniMap";
import { ScoreExplainer } from "./ScoreExplainer";
import { BattlecardCharts } from "./BattlecardCharts";
import { BattlecardInsights } from "./BattlecardInsights";

interface BattlecardDrawerProps {
  battlecard: Battlecard | null;
  areaName?: string;
  open: boolean;
  onClose: () => void;
  /** Download URL for the PDF export, when a catchment is loaded. */
  pdfUrl?: string;
  /** Download URL for the PPTX deck export. */
  pptxUrl?: string;
  /** Whether the run set a target price (else the pricing read is omitted). */
  priceSet?: boolean;
  /** The audience this run searched for, surfaced so the card is not generic. */
  audienceLabel?: string | null;
  /** Brownfield development sites that fall in this area (Find a site). */
  sites?: DevelopmentSite[];
  /** Whether the catchment has any sites at all, to tell "none here" from
   * "dataset not loaded". */
  catchmentHasSites?: boolean;
  /** Searched audience segment id, so its addressable pool is emphasised. */
  audienceSegment?: string | null;
  /** Geometry of this area, for the in-drawer plots map. */
  areaGeometry?: GeoJsonGeometry | null;
}

// Clicking a region opens its deep-dive in the slide-out drawer, never a full
// page navigation, so the map stays in view (design-framework.md, the map). The
// drawer is focus-managed. Battlecard prose uses the web output font.
export function BattlecardDrawer({
  battlecard,
  areaName,
  open,
  onClose,
  pdfUrl,
  pptxUrl,
  priceSet = true,
  audienceLabel,
  sites,
  catchmentHasSites,
  audienceSegment,
  areaGeometry,
}: BattlecardDrawerProps) {
  // Mount gate so the portal target (document.body) exists before rendering.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!mounted) return null;

  // Portal to the body so the fixed drawer is anchored to the viewport (full
  // height, top to bottom) regardless of any transformed or scrolled ancestor,
  // and sits above the mobile top bar and bottom tab bar.
  return createPortal(
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Area Battlecard"
      aria-hidden={!open}
      className={`fixed inset-y-0 right-0 z-[60] w-full max-w-md overflow-y-auto border-l border-neutral-200 bg-white p-5 shadow-none transition-transform duration-[280ms] ease-drawer ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
    >
      <div className="mb-4 flex justify-end">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close Battlecard"
          className="text-neutral-500 hover:text-neutral-900"
        >
          <X size={22} />
        </button>
      </div>

      {battlecard ? (
        <div className="space-y-6">
          {audienceLabel && (
            <span className="inline-block rounded-full bg-light-accent/10 px-3 py-1 text-xs font-semibold text-light-accent">
              Fit for {audienceLabel.toLowerCase()} in this area
            </span>
          )}
          <OnLocationSummary battlecard={battlecard} areaName={areaName} />

          {sites !== undefined && (
            <section className="rounded-card border border-neutral-200 p-4">
              <h3 className="mb-2 text-sm font-semibold">
                Development sites in this area{" "}
                <span className="font-normal text-neutral-400">
                  ({sites.length})
                </span>
              </h3>
              {open && sites.length > 0 && (
                <div className="mb-3">
                  <AreaMiniMap
                    key={battlecard.areaCode}
                    geometry={areaGeometry ?? null}
                    sites={sites}
                  />
                </div>
              )}
              {sites.length === 0 ? (
                <p className="text-xs text-neutral-500">
                  {catchmentHasSites
                    ? "No brownfield register sites fall in this area. Other areas in the catchment have plots, shown on the map and ranking."
                    : "No brownfield register sites loaded for this catchment. Load the Development sites data (Reference data) and re-run to see buildable plots."}
                </p>
              ) : (
                <ul className="max-h-72 space-y-1.5 overflow-y-auto pr-1">
                  {sites.map((s, i) => {
                    const cap =
                      s.minDwellings != null && s.maxDwellings != null
                        ? `${s.minDwellings} to ${s.maxDwellings} homes`
                        : s.maxDwellings != null
                          ? `${s.maxDwellings} homes`
                          : null;
                    const dot =
                      s.sourceType === "allocation"
                        ? "#C9A24B"
                        : s.sourceType === "permission"
                          ? "#C04A1F"
                          : "#1F5A3C";
                    return (
                      <li
                        key={s.reference ?? i}
                        className="flex items-start justify-between gap-2 text-xs"
                      >
                        <span className="flex min-w-0 flex-1 items-center gap-1.5">
                          <span
                            className="inline-block h-2 w-2 shrink-0 rounded-full"
                            style={{ backgroundColor: dot }}
                            aria-hidden
                          />
                          <span className="min-w-0 truncate text-neutral-700">
                            {s.name ?? s.reference ?? "Site"}
                          </span>
                        </span>
                        <span className="shrink-0 font-semibold text-light-accent">
                          {cap ?? (s.hectares != null ? `${s.hectares} ha` : "")}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
            </section>
          )}

          {(pdfUrl || pptxUrl) && (
            <div className="grid grid-cols-2 gap-2">
              {pdfUrl && (
                <a
                  href={pdfUrl}
                  className="flex items-center justify-center gap-2 rounded-card border border-neutral-300 py-2 text-sm font-semibold"
                >
                  <Download size={16} /> PDF
                </a>
              )}
              {pptxUrl && (
                <a
                  href={pptxUrl}
                  className="flex items-center justify-center gap-2 rounded-card border border-neutral-300 py-2 text-sm font-semibold"
                >
                  <Download size={16} /> PPTX
                </a>
              )}
            </div>
          )}

          {!battlecard.pricingRationale &&
            !battlecard.addressableSegments &&
            !battlecard.catchmentContext && (
              <p className="rounded-card border border-priority-mid/40 bg-priority-mid/10 p-3 text-xs text-neutral-600">
                This run predates the pricing rationale and addressable segment
                insights. Rebuild the catchment to generate the full Battlecard.
              </p>
            )}

          <BattlecardInsights
            pricing={battlecard.pricingRationale}
            segments={battlecard.addressableSegments}
            context={battlecard.catchmentContext}
            confidence={battlecard.dataConfidence}
            contextMetrics={battlecard.contextMetrics}
            objectiveLabel={battlecard.objectiveLabel}
            priceSet={priceSet}
            highlightSegment={audienceSegment ?? undefined}
          />

          {battlecard.visualSummary?.charts && (
            <BattlecardCharts charts={battlecard.visualSummary.charts} />
          )}

          {battlecard.score && <ScoreExplainer score={battlecard.score} />}

          {/* Page 2 and 3 commentary. Output font, signal-driven prose. */}
          {battlecard.incomeAndTenure && (
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
          )}
        </div>
      ) : (
        <p className="text-sm text-neutral-500">Loading Battlecard...</p>
      )}
    </div>,
    document.body,
  );
}
