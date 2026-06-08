import type { Metadata } from "next";
import {
  MapPin,
  Route,
  Layers,
  Target,
  FileDown,
  Building2,
  Dumbbell,
  Store,
  Landmark,
  ShieldCheck,
  Scale,
  Gauge,
  type LucideIcon,
} from "lucide-react";

export const metadata: Metadata = {
  title: "How it works - LandLynk",
};

// Explainer page: what the tool does, its value, the user flow and real use
// cases. Cards follow the design framework: 14px radius, 1px borders, no shadow.

function Card({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-card border border-neutral-200 p-5 dark:border-neutral-800">
      <Icon size={22} className="text-light-accent dark:text-dark-accent" />
      <h3 className="mt-3 text-sm font-semibold">{title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
        {children}
      </p>
    </div>
  );
}

export default function HowItWorksPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-12 p-4 py-8">
      {/* Hero */}
      <header className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-light-accent dark:text-dark-accent">
          The Geographic Intelligence Engine
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          Turn a location into a targeting strategy
        </h1>
        <p className="mt-3 text-base leading-relaxed text-neutral-600 dark:text-neutral-300">
          Paste a development postcode or an OS grid reference. LandLynk builds a
          realistic drive-time catchment, scores and ranks every area inside it
          on how worth targeting it is, and generates a Battlecard for each one
          that tells you who to target, how to price, and what to say. It is
          built entirely on open public data, so every ranking is reproducible
          and explainable.
        </p>
      </header>

      {/* Purpose and value */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Why it exists</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card icon={Target} title="Evidence, not assumption">
            Marketing strategy for a place is too often built on a hunch. LandLynk
            grounds it in ONS Census and income data for the actual catchment.
          </Card>
          <Card icon={Gauge} title="Seconds, not hours">
            Defining a catchment by eye used to take 15 to 30 minutes per site.
            Here it is an automated sub-second lookup, repeatable at scale.
          </Card>
          <Card icon={Scale} title="Ranked priorities">
            Areas are scored and ordered, so you see where to focus spend and
            sales effort first rather than reading a flat colour map.
          </Card>
          <Card icon={ShieldCheck} title="Explainable">
            Every score shows the signals behind it. Any ranking traces back to
            the data and the config that produced it.
          </Card>
          <Card icon={Layers} title="No data licences">
            Open public sources only, so there is no per-client data cost and the
            method is fully auditable and refreshable.
          </Card>
          <Card icon={FileDown} title="Ready to present">
            Each area exports to a PDF Battlecard and the catchment to a Google
            Earth KML, so outputs go straight into pitches and reviews.
          </Card>
        </div>
      </section>

      {/* How to use it */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">How you use it</h2>
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[
            {
              icon: MapPin,
              step: "1",
              title: "Enter a location",
              body: "Paste a postcode, or an OS grid reference for a site with no postcode yet. Add the scheme brief and price band if you have them.",
            },
            {
              icon: Route,
              step: "2",
              title: "Build the catchment",
              body: "LandLynk geocodes, draws a 30-minute drive-time zone and finds the areas inside it, weighted by how much of each falls in the zone.",
            },
            {
              icon: Layers,
              step: "3",
              title: "Read the ranked map",
              body: "Every area is colour-coded by priority and listed in rank order. Click any area to open its full Battlecard and deep-dive.",
            },
            {
              icon: FileDown,
              step: "4",
              title: "Export and act",
              body: "Download the PDF Battlecard per area or the KML catchment layer, and take the shortlist into your campaign and sales planning.",
            },
          ].map((s) => {
            const Icon = s.icon;
            return (
              <li
                key={s.step}
                className="rounded-card border border-neutral-200 p-5 dark:border-neutral-800"
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-light-accent text-xs font-semibold text-white dark:bg-dark-accent">
                    {s.step}
                  </span>
                  <Icon size={18} className="text-neutral-400" />
                </div>
                <h3 className="mt-3 text-sm font-semibold">{s.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-neutral-600 dark:text-neutral-300">
                  {s.body}
                </p>
              </li>
            );
          })}
        </ol>
      </section>

      {/* Use cases */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Real-world use cases</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Card icon={Building2} title="Residential new-build">
            For a new housing development, find the areas whose income, tenure and
            age profile fit the price band and bed mix, and tailor the message to
            first-time buyers, second steppers or downsizers by area.
          </Card>
          <Card icon={Dumbbell} title="Leisure centre catchment">
            For a gym or leisure centre, size the addressable population within a
            realistic drive time and prioritise the neighbourhoods most likely to
            convert to memberships.
          </Card>
          <Card icon={Store} title="Retail site selection">
            Compare candidate sites by the quality and scale of the catchment each
            one commands, with the demographics that match the retail format.
          </Card>
          <Card icon={Landmark} title="Local authority communications">
            Plan public consultation or service communications around the real
            population an area reaches, with confidence flags where data is thin.
          </Card>
        </div>
      </section>

      <section className="rounded-card border border-neutral-200 p-6 text-center dark:border-neutral-800">
        <h2 className="text-lg font-semibold">Ready to try it</h2>
        <p className="mx-auto mt-1 max-w-xl text-sm text-neutral-600 dark:text-neutral-300">
          Head to the catchment map, paste a postcode and build your first
          ranked catchment.
        </p>
        <a
          href="/"
          className="mt-4 inline-flex items-center gap-2 rounded-card bg-light-accent px-4 py-2 text-sm font-semibold text-white dark:bg-dark-accent"
        >
          <MapPin size={16} /> Open the catchment map
        </a>
      </section>
    </div>
  );
}
