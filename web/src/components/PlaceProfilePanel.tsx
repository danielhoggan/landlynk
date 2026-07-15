"use client";

import { useEffect, useState } from "react";
import {
  Bike,
  Bus,
  ChevronDown,
  Download,
  Loader2,
  MapPin,
  School,
  ShoppingBasket,
  TrainFront,
  Trees,
  UtensilsCrossed,
} from "lucide-react";
import {
  generatePlaceStory,
  getPlaceProfile,
  getUsage,
  type LlmUsage,
  type PlaceAmenity,
  type PlaceProfile,
} from "@/lib/client";

function dist(m: number): string {
  return m >= 950 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m / 10) * 10} m`;
}

function AmenityList({
  items,
  empty,
}: {
  items: PlaceAmenity[];
  empty: string;
}) {
  if (!items.length) {
    return <p className="text-xs text-neutral-500">{empty}</p>;
  }
  return (
    <ul className="space-y-0.5 text-xs text-neutral-600">
      {items.map((i) => (
        <li key={`${i.name}-${i.distanceM}`}>
          <span className="font-medium">{i.name}</span> · {dist(i.distanceM)}
        </li>
      ))}
    </ul>
  );
}

// The place around the development itself, anchored on the run's postcode
// pin: nearest station with walk and drive estimates, buses and their routes,
// restaurants and cycle routes (all factual, from OpenStreetMap, free) plus
// an optional AI story of annual events and local history (metered like the
// Local Area Profile). Development-specific, so it is offered on Plan the
// next phase only. Downloads as the Place setting pack deck.
export function PlaceProfilePanel({ catchmentId }: { catchmentId: string }) {
  const [place, setPlace] = useState<PlaceProfile | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [usage, setUsage] = useState<LlmUsage | null>(null);
  const [pending, setPending] = useState(false);
  const [packBusy, setPackBusy] = useState(false);

  // Fetch the pack as a blob so a failure shows inline instead of navigating
  // the page to a JSON error, and the button can show progress (the first
  // download can take up to half a minute while the AI slides generate).
  async function downloadPack() {
    if (packBusy) return;
    setPackBusy(true);
    setError("");
    try {
      const res = await fetch(`/api/catchments/${catchmentId}/place/pptx`);
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(
          data?.error ?? `Could not build the pack (${res.status})`,
        );
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "landlynk-place-pack.pptx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      // The download may have auto-generated the AI story; reflect it here.
      getPlaceProfile(catchmentId)
        .then((p) => p && setPlace(p))
        .catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not build the pack");
    } finally {
      setPackBusy(false);
    }
  }

  const load = (refresh = false) => {
    setLoaded(false);
    setPlace(null);
    getPlaceProfile(catchmentId, refresh)
      .then(setPlace)
      .catch(() => {})
      .finally(() => setLoaded(true));
  };

  useEffect(() => {
    let active = true;
    setLoaded(false);
    setPlace(null);
    getPlaceProfile(catchmentId)
      .then((p) => active && setPlace(p))
      .catch(() => {})
      .finally(() => active && setLoaded(true));
    getUsage()
      .then((u) => active && setUsage(u))
      .catch(() => {});
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        "month. Adding events, history and the political picture uses 1. The " +
        "transit and dining sections are free and already included."
      : "This adds an AI lookup of the location's annual events, history and " +
        "political picture. The transit and dining sections are free and " +
        "already included.";

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
            The place around your development, anchored on its postcode:
            transit, eating out and cycling from OpenStreetMap. Walk and drive
            times are approximate. The pack download auto-includes the AI
            events, history and political slides (1 AI lookup, first time
            only).
          </p>
          <button
            type="button"
            onClick={downloadPack}
            disabled={packBusy}
            title={
              place?.story
                ? "Download the Place setting pack"
                : "Downloads the full pack; the AI slides (events, history, political picture) generate automatically and use 1 AI lookup"
            }
            className="flex shrink-0 items-center gap-1.5 rounded-card border border-neutral-300 px-3 py-1.5 text-xs font-semibold text-neutral-600 hover:bg-neutral-100 disabled:opacity-60"
          >
            {packBusy ? (
              <Loader2 size={14} className="animate-spin" />
            ) : (
              <Download size={14} />
            )}
            {packBusy ? "Building pack..." : "Place setting pack"}
          </button>
        </div>

        {!place && !loaded && (
          <p className="text-xs text-neutral-500">
            Looking around the pin... (up to half a minute on first open)
          </p>
        )}
        {!place && loaded && (
          <p className="text-xs text-neutral-600">
            The map source did not answer just now.{" "}
            <button
              type="button"
              onClick={() => load(true)}
              className="font-semibold text-light-accent underline"
            >
              Try again
            </button>
          </p>
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
                  <p className="text-sm font-semibold">
                    {place.station.name}
                    {place.station.metro ? " (Metro)" : ""}
                  </p>
                  <p className="text-xs text-neutral-500">
                    {place.station.distanceKm} km · about{" "}
                    {place.station.walkMinutes} min walk or{" "}
                    {place.station.driveMinutes} min drive (approx)
                  </p>
                  {place.otherStations.map((s) => (
                    <p key={s.name} className="text-[11px] text-neutral-400">
                      Also {s.name}
                      {s.metro ? " (Metro)" : ""}, {s.distanceKm} km
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
                <Bus size={14} className="text-light-accent" /> Buses from the
                door
              </h3>
              {(place.busServices?.length ?? 0) > 0 ? (
                <ul className="space-y-0.5 text-xs text-neutral-600">
                  {place.busServices!.slice(0, 5).map((svc) => (
                    <li key={svc.ref}>
                      <span className="font-semibold">{svc.ref}</span> to{" "}
                      {svc.destinations.join(" / ") || "local service"}
                    </li>
                  ))}
                </ul>
              ) : place.busRoutes.length > 0 ? (
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
              ) : null}
              {place.busStops.length > 0 ? (
                <p className="mt-1.5 text-[11px] text-neutral-400">
                  Nearest stop {place.busStops[0].name},{" "}
                  {dist(place.busStops[0].distanceM)}
                </p>
              ) : (
                <p className="text-xs text-neutral-500">
                  No bus stops within 900 m.
                </p>
              )}
            </section>

            <section className="rounded-card border border-neutral-200 p-3">
              <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold">
                <ShoppingBasket size={14} className="text-light-accent" /> Shops
                and essentials
              </h3>
              <AmenityList
                items={[...(place.shops ?? []), ...(place.health ?? [])]
                  .sort((a, b) => a.distanceM - b.distanceM)
                  .slice(0, 6)}
                empty="No supermarkets, pharmacies or GPs mapped within 2 km."
              />
            </section>

            <section className="rounded-card border border-neutral-200 p-3">
              <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold">
                <School size={14} className="text-light-accent" /> Schools
              </h3>
              <AmenityList
                items={(place.schools ?? []).slice(0, 6)}
                empty="No schools mapped within 2 km on OpenStreetMap."
              />
            </section>

            <section className="rounded-card border border-neutral-200 p-3">
              <h3 className="mb-2 flex items-center gap-1.5 text-xs font-semibold">
                <Trees size={14} className="text-light-accent" /> Parks and
                leisure
              </h3>
              <AmenityList
                items={(place.parks ?? []).slice(0, 6)}
                empty="No named parks or leisure centres mapped within 1.5 km."
              />
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
            {busy ? "Adding..." : "Add events, history and political picture (AI)"}
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
            {place.story.politics && (
              <section className="rounded-card border border-neutral-200 p-3">
                <h3 className="mb-2 text-xs font-semibold">
                  The political picture
                </h3>
                {place.civic?.constituency && (
                  <p className="text-xs text-neutral-500">
                    {place.civic.constituency}
                    {place.civic.council ? ` · ${place.civic.council}` : ""}
                    {place.civic.ward ? ` · ${place.civic.ward} ward` : ""}
                  </p>
                )}
                <ul className="mt-1 space-y-0.5 text-xs text-neutral-600">
                  {/* The MP comes from official records (UK Parliament API),
                      never the model; older stories' guess is the fallback. */}
                  {(place.civic?.mp || place.story.politics.mp) && (
                    <li>
                      MP: {place.civic?.mp || place.story.politics.mp}
                      {(place.civic?.mp
                        ? place.civic?.mpParty
                        : place.story.politics.mpParty)
                        ? ` (${
                            place.civic?.mp
                              ? place.civic?.mpParty
                              : place.story.politics.mpParty
                          })`
                        : ""}
                    </li>
                  )}
                  {place.story.politics.councilControl && (
                    <li>
                      Council control: {place.story.politics.councilControl}
                    </li>
                  )}
                </ul>
                {place.story.politics.commentary && (
                  <p className="mt-1.5 text-xs text-neutral-600">
                    {place.story.politics.commentary}
                  </p>
                )}
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
