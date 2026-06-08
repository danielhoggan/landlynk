"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type {
  CatchmentArea,
  Coordinate,
  GeoJsonGeometry,
} from "@/lib/types/catchment";
import { PRIORITY_COLORS } from "@/lib/priority";

interface CatchmentMapProps {
  areas: CatchmentArea[];
  isochrone: GeoJsonGeometry | null;
  coordinate: Coordinate | null;
  onSelectArea: (area: CatchmentArea) => void;
  selectedAreaCode?: string;
}

// Open-source base map. OSM raster tiles are open data (ODbL); swap for
// self-hosted or other open tiles in production. No licensed tiles
// (design-framework.md, the map).
const BASE_STYLE: maplibregl.StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: "raster",
      tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
      tileSize: 256,
      attribution: "© OpenStreetMap contributors",
    },
  },
  layers: [{ id: "osm", type: "raster", source: "osm" }],
};

function areasToFeatures(areas: CatchmentArea[]): GeoJSON.FeatureCollection {
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
        },
      })),
  };
}

// The interactive catchment map (design-framework.md). The drive-time isochrone
// is a translucent overlay so the boundary stays visible; each region is
// clickable and colour-coded by priority band. Clicking opens the deep-dive
// without leaving the map.
export function CatchmentMap({
  areas,
  isochrone,
  coordinate,
  onSelectArea,
  selectedAreaCode,
}: CatchmentMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  // Keep the latest callback without re-binding map listeners.
  const onSelectRef = useRef(onSelectArea);
  onSelectRef.current = onSelectArea;
  const areasRef = useRef(areas);
  areasRef.current = areas;

  // Initialise the map once.
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

    map.on("load", () => {
      map.addSource("isochrone", { type: "geojson", data: emptyFc() });
      map.addLayer({
        id: "isochrone-fill",
        type: "fill",
        source: "isochrone",
        paint: { "fill-color": "#0071E3", "fill-opacity": 0.08 },
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
          "fill-opacity": 0.55,
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
      map.on("mouseenter", "areas-fill", () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", "areas-fill", () => {
        map.getCanvas().style.cursor = "";
      });

      mapRef.current = map;
      // Draw any data that arrived before load completed.
      syncData();
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Push area, isochrone and pin updates to the map.
  function syncData() {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const areaSource = map.getSource("areas") as
      | maplibregl.GeoJSONSource
      | undefined;
    areaSource?.setData(areasToFeatures(areas));

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
  }, [areas, isochrone, coordinate]);

  // Highlight the selected region.
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

// Compute a bounding box from a polygon or multipolygon geometry.
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
