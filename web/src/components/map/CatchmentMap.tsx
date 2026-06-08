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
import { tagsForArea } from "@/lib/areaTags";

interface CatchmentMapProps {
  areas: CatchmentArea[];
  isochrone: GeoJsonGeometry | null;
  coordinate: Coordinate | null;
  onSelectArea: (area: CatchmentArea) => void;
  selectedAreaCode?: string;
  /** Area codes passing the active filter; others are dimmed. null = no filter. */
  matchedCodes?: Set<string> | null;
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
): GeoJSON.FeatureCollection {
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
          ownerOccupied: a.metrics?.ownerOccupied ?? null,
          tags: tagsForArea(a)
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
export function CatchmentMap({
  areas,
  isochrone,
  coordinate,
  onSelectArea,
  selectedAreaCode,
  matchedCodes,
}: CatchmentMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  const popupRef = useRef<maplibregl.Popup | null>(null);
  const onSelectRef = useRef(onSelectArea);
  onSelectRef.current = onSelectArea;
  const areasRef = useRef(areas);
  areasRef.current = areas;

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
      closeButton: false,
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
          "fill-color": [
            "match",
            ["get", "band"],
            "high",
            PRIORITY_COLORS.high,
            "mid",
            PRIORITY_COLORS.mid,
            "low",
            PRIORITY_COLORS.low,
            "#999999",
          ],
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

      map.on("click", "areas-fill", (e) => {
        const code = e.features?.[0]?.properties?.areaCode as
          | string
          | undefined;
        if (!code) return;
        const area = areasRef.current.find((a) => a.areaCode === code);
        if (area) onSelectRef.current(area);
      });
      map.on("mousemove", "areas-fill", (e) => {
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
               <div>Owner-occupied: ${fmtPct(p.ownerOccupied as number | null)}</div>
               ${tags ? `<div class="mt-1 text-light-accent">${escapeHtml(tags)}</div>` : ""}
             </div>`,
          )
          .addTo(map);
      });
      map.on("mouseleave", "areas-fill", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });

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
    if (!map || !map.isStyleLoaded()) return;

    const areaSource = map.getSource("areas") as
      | maplibregl.GeoJSONSource
      | undefined;
    areaSource?.setData(areasToFeatures(areas, matchedCodes));

    const isoSource = map.getSource("isochrone") as
      | maplibregl.GeoJSONSource
      | undefined;
    if (isochrone) {
      isoSource?.setData({
        type: "Feature",
        geometry: isochrone as GeoJSON.Geometry,
        properties: {},
      });
      const b = bounds(isochrone as GeoJSON.Geometry);
      if (b) map.fitBounds(b, { padding: 40, duration: 600 });
    } else {
      isoSource?.setData(emptyFc());
    }

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
  }, [areas, isochrone, coordinate, matchedCodes]);

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
