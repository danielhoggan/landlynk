"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type {
  CatchmentArea,
  Coordinate,
  GeoJsonGeometry,
} from "@/lib/types/catchment";
import { PRIORITY_COLORS, PRIORITY_LABELS } from "@/lib/priority";
import { tagsForArea, type TagContext } from "@/lib/areaTags";
import type { DevelopmentSite, CouncilBoundary } from "@/lib/client";

/** Metric the area fill is shaded by; "band" is the priority ranking. */
export type ShadeBy = "band" | "income" | "housePrice" | "ownerOccupied";

/** Choropleth ramp, light to dark LandLynk green; grey marks no data. */
export const SHADE_RAMP = ["#E7F0E9", "#1F5A3C"] as const;
export const SHADE_NO_DATA = "#CBCBCB";

interface CatchmentMapProps {
  areas: CatchmentArea[];
  isochrone: GeoJsonGeometry | null;
  coordinate: Coordinate | null;
  onSelectArea: (area: CatchmentArea) => void;
  selectedAreaCode?: string;
  /** Area codes passing the active filter; others are dimmed. null = no filter. */
  matchedCodes?: Set<string> | null;
  /** Catchment-derived context for relative signal tags. */
  tagContext?: TagContext;
  /** Brownfield development sites to overlay (Find a site). */
  sites?: DevelopmentSite[];
  /** Shade the areas by a data metric instead of the priority band. */
  shadeBy?: ShadeBy;
  /** Council (LA) boundaries to outline and label over the areas. */
  councils?: CouncilBoundary[];
}

// Open vector base map. OpenFreeMap is free, OSM-based and needs no API key, so
// it fits the no-licensed-tiles rule (design-framework.md, the map). Override
// with NEXT_PUBLIC_MAP_STYLE to point at a self-hosted style for production.
const BASE_STYLE: string =
  process.env.NEXT_PUBLIC_MAP_STYLE ??
  "https://tiles.openfreemap.org/styles/liberty";

const fmtMoney = (v: number | null | undefined) =>
  v == null ? "n/a" : `£${Math.round(v).toLocaleString()}`;
const fmtPct = (v: number | null | undefined) =>
  v == null ? "n/a" : `${v.toFixed(1)}%`;

function areasToFeatures(
  areas: CatchmentArea[],
  matchedCodes: Set<string> | null | undefined,
  tagContext?: TagContext,
  shadeBy: ShadeBy = "band",
): GeoJSON.FeatureCollection {
  const shade = shadeColours(areas, shadeBy);
  return {
    type: "FeatureCollection",
    features: areas
      .filter((a) => a.geometry)
      .map((a) => ({
        type: "Feature",
        geometry: a.geometry as GeoJSON.Geometry,
        properties: {
          areaCode: a.areaCode,
          band: a.band,
          rank: a.rank,
          name: a.name,
          score: a.score,
          income: a.metrics?.income ?? null,
          housePrice: a.metrics?.housePrice ?? null,
          ownerOccupied: a.metrics?.ownerOccupied ?? null,
          shadeColor: shade(a),
          tags: tagsForArea(a, tagContext)
            .map((t) => t.label)
            .join(", "),
          match: matchedCodes ? (matchedCodes.has(a.areaCode) ? 1 : 0) : 1,
        },
      })),
  };
}

// The interactive catchment map (design-framework.md). The drive-time isochrone
// is a translucent overlay; each region is colour-coded by priority band,
// dimmed when filtered out, hoverable for its key numbers, and clickable to open
// the deep-dive.
// The priority-band fill, the default shading.
const BAND_FILL: maplibregl.ExpressionSpecification = [
  "match",
  ["get", "band"],
  "high",
  PRIORITY_COLORS.high,
  "mid",
  PRIORITY_COLORS.mid,
  "low",
  PRIORITY_COLORS.low,
  "#999999",
];

function hexLerp(a: string, b: string, t: number): string {
  const pa = [1, 3, 5].map((i) => parseInt(a.slice(i, i + 2), 16));
  const pb = [1, 3, 5].map((i) => parseInt(b.slice(i, i + 2), 16));
  return `#${pa
    .map((v, i) =>
      Math.round(v + (pb[i] - v) * t)
        .toString(16)
        .padStart(2, "0"),
    )
    .join("")}`;
}

// Colour per area for the chosen shading: a linear ramp over the metric's
// range in this catchment, grey where the area has no value. Computed in JS
// and stored on the feature, so the paint layer just reads it.
function shadeColours(
  areas: CatchmentArea[],
  shadeBy: ShadeBy,
): (a: CatchmentArea) => string | null {
  if (shadeBy === "band") return () => null;
  const vals = areas
    .map((a) => a.metrics?.[shadeBy])
    .filter((v): v is number => v != null);
  const min = vals.length ? Math.min(...vals) : 0;
  const max = vals.length ? Math.max(...vals) : 0;
  return (a) => {
    const v = a.metrics?.[shadeBy];
    if (v == null || !vals.length) return SHADE_NO_DATA;
    if (min === max) return SHADE_RAMP[1];
    return hexLerp(SHADE_RAMP[0], SHADE_RAMP[1], (v - min) / (max - min));
  };
}

export function CatchmentMap({
  areas,
  isochrone,
  coordinate,
  onSelectArea,
  selectedAreaCode,
  matchedCodes,
  tagContext,
  sites,
  shadeBy = "band",
  councils,
}: CatchmentMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const onSelectRef = useRef(onSelectArea);
  onSelectRef.current = onSelectArea;
  const areasRef = useRef(areas);
  areasRef.current = areas;
  const tagContextRef = useRef(tagContext);
  tagContextRef.current = tagContext;
  const sitesRef = useRef(sites);
  sitesRef.current = sites;
  // The last run framed by fitBounds, so re-syncs (filters, overlays) never
  // re-zoom a view the user has adjusted.
  const framedKeyRef = useRef<string>("");

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASE_STYLE,
      center: [-1.5, 52.8],
      zoom: 5,
    });
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    const popup = new maplibregl.Popup({
      // A close button so a tapped plot popup can be dismissed on mobile, where
      // there is no hover to clear it.
      closeButton: true,
      closeOnClick: false,
      offset: 12,
      className: "ll-popup",
    });
    popupRef.current = popup;

    map.on("load", () => {
      map.addSource("isochrone", { type: "geojson", data: emptyFc() });
      map.addLayer({
        id: "isochrone-fill",
        type: "fill",
        source: "isochrone",
        paint: { "fill-color": "#0071E3", "fill-opacity": 0.06 },
      });
      map.addLayer({
        id: "isochrone-line",
        type: "line",
        source: "isochrone",
        paint: { "line-color": "#0071E3", "line-width": 2 },
      });

      map.addSource("areas", { type: "geojson", data: emptyFc() });
      map.addLayer({
        id: "areas-fill",
        type: "fill",
        source: "areas",
        paint: {
          "fill-color": BAND_FILL,
          // Dim areas filtered out.
          "fill-opacity": ["case", ["==", ["get", "match"], 1], 0.55, 0.07],
        },
      });
      map.addLayer({
        id: "areas-line",
        type: "line",
        source: "areas",
        paint: { "line-color": "#FFFFFF", "line-width": 1 },
      });

      // Council (LA) boundaries: dashed outlines with a labelled name, drawn
      // over the areas but under the site dots.
      map.addSource("councils", { type: "geojson", data: emptyFc() });
      map.addLayer({
        id: "councils-line",
        type: "line",
        source: "councils",
        paint: {
          "line-color": "#334155",
          "line-width": 1.5,
          "line-dasharray": [3, 2],
        },
      });
      map.addLayer({
        id: "councils-label",
        type: "symbol",
        source: "councils",
        layout: {
          "text-field": ["get", "name"],
          "text-size": 11,
          "text-font": ["Noto Sans Regular"],
        },
        paint: {
          "text-color": "#334155",
          "text-halo-color": "#FFFFFF",
          "text-halo-width": 1.2,
        },
      });

      map.on("click", "areas-fill", (e) => {
        // A tap on a plot dot should show the plot, not open the area beneath
        // it (the dots sit on top of the area fill, but a tap falls through).
        if (
          map.getLayer("sites-circle") &&
          map.queryRenderedFeatures(e.point, { layers: ["sites-circle"] }).length
        ) {
          return;
        }
        const code = e.features?.[0]?.properties?.areaCode as
          | string
          | undefined;
        if (!code) return;
        const area = areasRef.current.find((a) => a.areaCode === code);
        if (area) onSelectRef.current(area);
      });
      // A tap fires synthetic mouse events: mousemove opens the hover popup and
      // the synthetic hover then ends, so mouseleave removes it a beat later.
      // Hover popups are therefore bound only where a real pointer can hover;
      // on touch, taps open popups via click and the close button dismisses.
      const canHover = window.matchMedia("(hover: hover)").matches;

      if (canHover) map.on("mousemove", "areas-fill", (e) => {
        const f = e.features?.[0];
        if (!f) return;
        map.getCanvas().style.cursor = "pointer";
        const p = f.properties as Record<string, unknown>;
        const tags = (p.tags as string) || "";
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div class="text-xs">
               <div class="font-semibold text-sm">#${p.rank} ${escapeHtml(String(p.name ?? ""))}</div>
               <div class="text-neutral-500">${PRIORITY_LABELS[p.band as "high" | "mid" | "low"]} · score ${Number(p.score).toFixed(2)}</div>
               <div class="mt-1">Avg income: ${fmtMoney(p.income as number | null)}</div>
               <div>House price: ${fmtMoney(p.housePrice as number | null)}</div>
               <div>Owner-occupied: ${fmtPct(p.ownerOccupied as number | null)}</div>
               ${tags ? `<div class="mt-1 text-light-accent">${escapeHtml(tags)}</div>` : ""}
             </div>`,
          )
          .addTo(map);
      });
      if (canHover) map.on("mouseleave", "areas-fill", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });

      // Brownfield development sites, drawn above the areas (Find a site).
      map.addSource("sites", { type: "geojson", data: emptyFc() });
      map.addLayer({
        id: "sites-circle",
        type: "circle",
        source: "sites",
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 5, 10, 7, 14, 10],
          "circle-color": [
            "match",
            ["get", "sourceType"],
            "permission",
            "#C04A1F",
            "#1F5A3C",
          ],
          "circle-stroke-color": "#FFFFFF",
          "circle-stroke-width": 1.5,
          "circle-opacity": 0.9,
        },
      });
      const showSitePopup = (e: maplibregl.MapLayerMouseEvent) => {
        const p = e.features?.[0]?.properties as Record<string, unknown>;
        if (!p) return;
        const cap = p.capacity ? String(p.capacity) : "";
        const typeLabel =
          p.sourceType === "permission"
            ? "Competitor development"
            : "Brownfield land";
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div class="text-xs">
               <div class="font-semibold text-sm">${escapeHtml(String(p.name || "Development site"))}</div>
               <div class="text-neutral-500">${typeLabel}</div>
               ${cap ? `<div>${escapeHtml(cap)} dwellings</div>` : ""}
               ${p.hectares ? `<div>${escapeHtml(String(p.hectares))} ha</div>` : ""}
             </div>`,
          )
          .addTo(map);
      };
      if (canHover) map.on("mousemove", "sites-circle", (e) => {
        map.getCanvas().style.cursor = "pointer";
        showSitePopup(e);
      });
      if (canHover) map.on("mouseleave", "sites-circle", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
      // Tap a plot (mobile, where there is no hover) to see it, instead of the
      // tap falling through to the area beneath.
      map.on("click", "sites-circle", showSitePopup);

      mapRef.current = map;
      syncData();
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function syncData() {
    const map = mapRef.current;
    if (!map) return;
    // Sources are added on style load; if the style is not ready yet (data can
    // arrive after the async run, e.g. the sites overlay), retry once it is,
    // otherwise the layer silently never gets its data.
    if (!map.isStyleLoaded() || !map.getSource("sites")) {
      map.once("idle", syncData);
      return;
    }

    const areaFc = areasToFeatures(
      areas,
      matchedCodes,
      tagContextRef.current,
      shadeBy,
    );
    const areaSource = map.getSource("areas") as
      | maplibregl.GeoJSONSource
      | undefined;
    areaSource?.setData(areaFc);
    // Shade by the chosen metric's per-feature colour (or the priority band).
    map.setPaintProperty(
      "areas-fill",
      "fill-color",
      shadeBy === "band"
        ? BAND_FILL
        : (["get", "shadeColor"] as maplibregl.ExpressionSpecification),
    );

    const councilSource = map.getSource("councils") as
      | maplibregl.GeoJSONSource
      | undefined;
    councilSource?.setData({
      type: "FeatureCollection",
      features: (councils ?? []).map((c) => ({
        type: "Feature",
        geometry: c.geometry as GeoJSON.Geometry,
        properties: { name: c.name },
      })),
    });

    const isoSource = map.getSource("isochrone") as
      | maplibregl.GeoJSONSource
      | undefined;
    if (isochrone) {
      isoSource?.setData({
        type: "Feature",
        geometry: isochrone as GeoJSON.Geometry,
        properties: {},
      });
    } else {
      isoSource?.setData(emptyFc());
    }

    // Frame the catchment: prefer the isochrone outline, falling back to the
    // area polygons when there is none (radius-mode or older runs), otherwise
    // the map stays at the UK-wide default zoom. Re-frame only when the run
    // itself changes, never on filter toggles or when the competitor overlay
    // arrives seconds later, so a zoom the user has set is not yanked away.
    const frameKey = `${areas.map((a) => a.areaCode).join(",")}|${
      isochrone ? "iso" : "none"
    }`;
    if (frameKey !== framedKeyRef.current) {
      let frame: maplibregl.LngLatBoundsLike | null = isochrone
        ? bounds(isochrone as GeoJSON.Geometry)
        : null;
      if (!frame) frame = boundsOfFeatures(areaFc);
      if (frame) {
        map.fitBounds(frame, { padding: 40, duration: 600 });
        framedKeyRef.current = frameKey;
      }
    }

    const sitesSource = map.getSource("sites") as
      | maplibregl.GeoJSONSource
      | undefined;
    sitesSource?.setData(sitesToFeatures(sitesRef.current));

    markerRef.current?.remove();
    if (coordinate) {
      markerRef.current = new maplibregl.Marker({ color: "#0071E3" })
        .setLngLat([coordinate.lng, coordinate.lat])
        .addTo(map);
    }
  }

  useEffect(() => {
    syncData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [areas, isochrone, coordinate, matchedCodes, sites, shadeBy, councils]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("areas-line")) return;
    map.setPaintProperty("areas-line", "line-width", [
      "case",
      ["==", ["get", "areaCode"], selectedAreaCode ?? ""],
      3,
      1,
    ]);
  }, [selectedAreaCode]);

  return (
    <div
      ref={containerRef}
      className="h-[60vh] min-h-[360px] w-full overflow-hidden rounded-card border border-neutral-200"
      role="application"
      aria-label="Catchment map"
    />
  );
}

function emptyFc(): GeoJSON.FeatureCollection {
  return { type: "FeatureCollection", features: [] };
}

function sitesToFeatures(
  sites: DevelopmentSite[] | undefined,
): GeoJSON.FeatureCollection {
  const capacity = (s: DevelopmentSite) =>
    s.minDwellings != null && s.maxDwellings != null
      ? `${s.minDwellings} to ${s.maxDwellings}`
      : (s.maxDwellings ?? s.minDwellings ?? null);
  return {
    type: "FeatureCollection",
    features: (sites ?? []).map((s) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [s.lng, s.lat] },
      properties: {
        name: s.name ?? "Development site",
        capacity: capacity(s),
        hectares: s.hectares,
        sourceType: s.sourceType,
      },
    })),
  };
}

function escapeHtml(s: string): string {
  return s.replace(
    /[&<>"]/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] as string,
  );
}

function bounds(
  geometry: GeoJSON.Geometry,
): maplibregl.LngLatBoundsLike | null {
  const b = new maplibregl.LngLatBounds();
  const extend = (coords: number[]) => b.extend([coords[0], coords[1]]);
  const walk = (arr: unknown): void => {
    if (Array.isArray(arr) && typeof arr[0] === "number") {
      extend(arr as number[]);
    } else if (Array.isArray(arr)) {
      arr.forEach(walk);
    }
  };
  if ("coordinates" in geometry)
    walk((geometry as { coordinates: unknown }).coordinates);
  return b.isEmpty() ? null : b;
}

// Combined bounds of every feature in a collection, so the map can frame the
// ranked areas when there is no isochrone outline to fit to.
function boundsOfFeatures(
  fc: GeoJSON.FeatureCollection,
): maplibregl.LngLatBoundsLike | null {
  const b = new maplibregl.LngLatBounds();
  for (const f of fc.features) {
    if (!f.geometry) continue;
    const sub = bounds(f.geometry);
    if (sub) b.extend(sub as maplibregl.LngLatBounds);
  }
  return b.isEmpty() ? null : b;
}
