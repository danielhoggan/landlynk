"use client";

import { useEffect, useState } from "react";
import {
  Bike,
  Bus,
  ChevronDown,
  Download,
  MapPin,
  TrainFront,
  UtensilsCrossed,
} from "lucide-react";
import {
  generatePlaceStory,
  getPlaceProfile,
  getUsage,
  type LlmUsage,
  type PlaceProfile,
} from "@/lib/client";

function dist(m: number): string {
  return m >= 950 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m / 10) * 10} m`;
}

// The place itself, around the searched pin: nearest station with walk and
// drive estimates, buses and their routes, restaurants and cycle routes (all
// factual, from OpenStreetMap, free) plus an optional AI story of annual
// events and local history (metered like the Local Area Profile). Downloads
// as the Place setting pack deck.
export function PlaceProfilePanel({ catchmentId }: { catchmentId: string }) {
  const [place, setPlace] = useState<PlaceProfile | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [usage, setUsage] = useState<LlmUsage | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let active = true;
    setPlace(null);
    getPlaceProfile(catchmentId)
      .then((p) => active && setPlace(p))
      .catch(() => {});
    getUsage()
      .then((u) => active && setUsage(u))
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [catchmentId]);

  async function addStory() {
    setBusy(true);
    setError("");
    setPending(false);
    try {
      const story = await generatePlaceStory(catchmentId);
      setPlace((p) => (p ? { ...p, story } : p));
      getUsage()
        .then(setUsage)
        .catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not generate the story");
    } finally {
      setBusy(false);
    }
  }

  const metered = usage?.metered === true;
  const exhausted = metered && usage?.remaining != null && usage.remaining <= 0;
  const confirmText =
    metered && usage?.cap != null
      ? `You have ${usage?.remaining ?? 0} of ${usage.cap} AI lookups left this ` +
        "month. Adding events and history uses 1. The transit and dining " +
        "sections are free and already included."
      : "This adds an AI lookup of the location's annual events and history. " +
        "The transit and dining sections are free and already included.";

  return (
    <details className="group rounded-card border border-neutral-200 bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 p-4 text-sm font-semibold">
        <span className="flex flex-wrap items-center gap-2">
          <MapPin size={16} className="text-light-accent" /> Place profile
          {place?.story && (
            <span className="rounded-full bg-light-accent/10 px-2 py-0.5 text-[10px] font-semibold text-light-accent">
              Events and history added
            </span>
          )}
        </span>
        <ChevronDown
          size={16}
          className="shrink-0 text-neutral-400 transition-transform group-open:rotate-180"
        />
      </summary>
      <div className="space-y-4 px-4 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-neutral-500">
            The place around the pin: transit, eating out and cycling from
            OpenStreetMap. Walk and drive times are approximate.
          </p>
          <a
            href={`/api/catchments/${catchmentId}/place/pptx`}
            className="flex shrink-0 items-center gap-1.5 rounded-card border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-100"
          >
            <Download size={14} /> Place setting pack
          </a>
        </div>

        {!place && !error && (
          <p className="text-xs text-neutral-500">Looking around the pin...</p>
        )}
        {error && <p className="text-xs text-priority-low">{error}</p>}

        {place && (
          <div className="grid gap-3 sm:grid-cols-2">
            <section className="rounded-card border border-neutral-200 p-3">
              <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold">
                <TrainFront size={14} className="text-light-accent" /> Nearest
                station
              </h3>
              {place.station ? (
                <>
                  <p className="text-sm font-semibold">{place.station.name}</p>
                  <p className="text-xs text-neutral-500">
                    {place.station.distanceKm} km · about{" "}
                    {place.station.walkMinutes} min walk or{" "}
                    {place.station.driveMinutes} min drive (approx)
                  </p>
                  {place.otherStations.map((s) => (
                    <p key={s.name} className="text-[11px] text-neutral-400">
                      Also {s.name}, {s.distanceKm} km
                    </p>
                  ))}
                </>
              ) : (
                <p className="text-xs text-neutral-500">
                  No railway station within 8 km.
                </p>
              )}
            </section>

            <section className="rounded-card border border-neutral-200 p-3">
              <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold">
                <Bus size={14} className="text-light-accent" /> Buses nearby
              </h3>
              {place.busRoutes.length > 0 && (
                <div className="mb-1.5 flex flex-wrap gap-1">
                  {place.busRoutes.map((r) => (
                    <span
                      key={r}
                      className="rounded-full bg-neutral-100 px-2 py-0.5 text-[11px] font-semibold text-neutral-600"
                    >
                      {r}
                    </span>
                  ))}
                </div>
              )}
              {place.busStops.length > 0 ? (
                <ul className="space-y-0.5 text-xs text-neutral-600">
                  {place.busStops.slice(0, 4).map((s) => (
                    <li key={s.name}>
                      {s.name} · {dist(s.distanceM)}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-neutral-500">
                  No bus stops within 900 m.
                </p>
              )}
            </section>

            <section className="rounded-card border border-neutral-200 p-3">
              <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold">
                <UtensilsCrossed size={14} className="text-light-accent" /> Food
                and drink
              </h3>
              {place.restaurants.length > 0 ? (
                <ul className="space-y-0.5 text-xs text-neutral-600">
                  {place.restaurants.slice(0, 6).map((r) => (
                    <li key={`${r.name}-${r.distanceM}`}>
                      <span className="font-medium">{r.name}</span> ·{" "}
                      {dist(r.distanceM)}
                      {r.cuisine ? ` · ${r.cuisine}` : ""}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-neutral-500">
                  No named restaurants, cafes or pubs within 1.5 km.
                </p>
              )}
            </section>

            <section className="rounded-card border border-neutral-200 p-3">
              <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold">
                <Bike size={14} className="text-light-accent" /> Cycle routes
              </h3>
              {place.cycleRoutes.length > 0 ? (
                <ul className="space-y-0.5 text-xs text-neutral-600">
                  {place.cycleRoutes.map((c, i) => (
                    <li key={i}>
                      {c.ref ? `NCN ${c.ref}` : ""}
                      {c.ref && c.name ? " · " : ""}
                      {c.name ?? ""}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-neutral-500">
                  No named cycle routes within 3 km.
                </p>
              )}
            </section>
          </div>
        )}

        {place && !place.story && !pending && (
          <button
            type="button"
            onClick={() => setPending(true)}
            disabled={busy || exhausted}
            className="rounded-card bg-light-accent px-3 py-1.5 text-xs font-semibold text-white transition hover:brightness-95 disabled:opacity-50"
          >
            {busy ? "Adding..." : "Add events and history (AI)"}
          </button>
        )}

        {pending && (
          <div className="rounded-card border border-priority-mid/40 bg-priority-mid/10 p-2.5 text-xs">
            <p className="text-neutral-700">{confirmText} Are you sure?</p>
            <div className="mt-2 flex gap-2">
              <button
                type="button"
                onClick={addStory}
                className="rounded-card bg-light-accent px-3 py-1 font-semibold text-white"
              >
                {metered && usage?.cap != null ? "Use 1 lookup" : "Add lookup"}
              </button>
              <button
                type="button"
                onClick={() => setPending(false)}
                className="rounded-card border border-neutral-300 px-3 py-1 font-semibold"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {place?.story && (
          <div className="space-y-3">
            {place.story.events.length > 0 && (
              <section className="rounded-card border border-neutral-200 p-3">
                <h3 className="mb-2 text-xs font-semibold">
                  Events and festivals through the year
                </h3>
                <ul className="space-y-1.5 text-xs text-neutral-600">
                  {place.story.events.map((e, i) => (
                    <li key={i}>
                      <span className="font-medium">{e.name}</span>
                      {e.when ? ` · ${e.when}` : ""}
                      {e.description ? `. ${e.description}` : ""}
                    </li>
                  ))}
                </ul>
              </section>
            )}
            {place.story.history && (
              <section className="rounded-card border border-neutral-200 p-3">
                <h3 className="mb-2 text-xs font-semibold">
                  The story of the place
                </h3>
                <p className="output-prose text-sm leading-relaxed">
                  {place.story.history}
                </p>
              </section>
            )}
            <p className="text-[11px] text-neutral-400">
              Events and history are AI-generated
              {place.story.model ? ` by ${place.story.model}` : ""}. Please
              review before use. Included in the Place setting pack.
            </p>
          </div>
        )}
      </div>
    </details>
  );
}
