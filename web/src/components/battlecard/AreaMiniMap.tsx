"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { GeoJsonGeometry } from "@/lib/types/catchment";
import type { DevelopmentSite } from "@/lib/client";

const BASE_STYLE: string =
  process.env.NEXT_PUBLIC_MAP_STYLE ??
  "https://tiles.openfreemap.org/styles/liberty";

const SITE_COLOR: maplibregl.ExpressionSpecification = [
  "match",
  ["get", "sourceType"],
  "allocation",
  "#C9A24B",
  "permission",
  "#C04A1F",
  "#1F5A3C",
];

// A focused map of one area and the development plots inside it, shown in the
// Battlecard drawer so a user sees exactly where the plots sit. Remounts per
// area (keyed by the caller) so it stays simple, no live diffing.
export function AreaMiniMap({
  geometry,
  sites,
}: {
  geometry: GeoJsonGeometry | null;
  sites: DevelopmentSite[];
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current) return;
    const map = new maplibregl.Map({
      container: ref.current,
      style: BASE_STYLE,
      attributionControl: false,
    });
    map.addControl(
      new maplibregl.NavigationControl({ showCompass: false }),
      "top-right",
    );
    const popup = new maplibregl.Popup({ closeButton: false, offset: 10 });

    map.on("load", () => {
      const b = new maplibregl.LngLatBounds();
      let any = false;

      if (geometry) {
        map.addSource("area", {
          type: "geojson",
          data: { type: "Feature", geometry: geometry as GeoJSON.Geometry, properties: {} },
        });
        map.addLayer({
          id: "area-fill",
          type: "fill",
          source: "area",
          paint: { "fill-color": "#0071E3", "fill-opacity": 0.06 },
        });
        map.addLayer({
          id: "area-line",
          type: "line",
          source: "area",
          paint: { "line-color": "#0071E3", "line-width": 1.5 },
        });
        const walk = (c: unknown): void => {
          if (Array.isArray(c) && typeof c[0] === "number") {
            b.extend(c as [number, number]);
            any = true;
          } else if (Array.isArray(c)) {
            c.forEach(walk);
          }
        };
        walk((geometry as { coordinates?: unknown }).coordinates);
      }

      map.addSource("plots", {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: sites.map((s) => ({
            type: "Feature",
            geometry: { type: "Point", coordinates: [s.lng, s.lat] },
            properties: {
              sourceType: s.sourceType,
              name: s.name ?? s.reference ?? "Site",
            },
          })),
        },
      });
      map.addLayer({
        id: "plots",
        type: "circle",
        source: "plots",
        paint: {
          "circle-radius": 6,
          "circle-color": SITE_COLOR,
          "circle-stroke-color": "#FFFFFF",
          "circle-stroke-width": 1.5,
        },
      });
      sites.forEach((s) => {
        b.extend([s.lng, s.lat]);
        any = true;
      });

      map.on("mouseenter", "plots", () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", "plots", () => {
        map.getCanvas().style.cursor = "";
        popup.remove();
      });
      map.on("mousemove", "plots", (e) => {
        const name = e.features?.[0]?.properties?.name as string | undefined;
        if (name) popup.setLngLat(e.lngLat).setHTML(`<div class="text-xs">${name}</div>`).addTo(map);
      });

      if (any) map.fitBounds(b, { padding: 28, maxZoom: 15, duration: 0 });
    });

    return () => map.remove();
  }, [geometry, sites]);

  return (
    <div
      ref={ref}
      className="h-48 w-full overflow-hidden rounded-card border border-neutral-200"
      aria-label="Area and plots map"
    />
  );
}
