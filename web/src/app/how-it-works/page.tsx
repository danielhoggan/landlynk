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
  Ruler,
  Star,
  Sparkles,
  Palette,
  Users,
  Presentation,
  type LucideIcon,
} from "lucide-react";

export const metadata: Metadata = {
  title: "How it works - LandLynk",
};

// Explainer page: what the tool does, its value, the user flow, the richer
// capabilities and real use cases. Cards follow the design framework: 14px
// radius, 1px borders, no shadow.

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
    <div className="rounded-card border border-neutral-200 p-5">
      <Icon size={22} className="text-light-accent" />
      <h3 className="mt-3 text-sm font-semibold">{title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-neutral-600">{children}</p>
    </div>
  );
}

export default function HowItWorksPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-12 p-4 py-8">
      {/* Hero */}
      <header className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-light-accent">
          The Geographic Intelligence Engine
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          Turn a location into a targeting strategy
        </h1>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          Paste a development postcode or an OS grid reference. LandLynk builds a
          catchment, by drive time or by radius, scores and ranks every area
          inside it on how worth targeting it is, and generates a Battlecard for
          each one that tells you who to target, how to price and what to say.
          Rank for a specific audience segment, combine areas into a wider
          catchment, add an AI local area lookup, and export brand-themed decks.
          It is built on open public data, so every ranking is reproducible and
          explainable.
        </p>
      </header>

      {/* Purpose and value */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Why it exists</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card icon={Target} title="Evidence, not assumption">
            Marketing strategy for a place is too often built on a hunch.
            LandLynk grounds it in ONS Census and income data for the actual
            catchment.
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
          <Card icon={Presentation} title="Ready to present">
            Each area exports to a single-slide Battlecard as PDF or PowerPoint,
            themed to the client brand, plus a Google Earth KML of the catchment.
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
              title: "Enter a location and brief",
              body: "Paste a postcode or OS grid reference. Pick a builder profile to fill the brief in one click, or set the scheme, price band and a target audience segment yourself.",
            },
            {
              icon: Route,
              step: "2",
              title: "Choose the catchment",
              body: "Build a 30-minute drive-time zone, or switch to a straight radius for dense cities. LandLynk finds the areas inside it, weighted by how much of each falls in the zone.",
            },
            {
              icon: Layers,
              step: "3",
              title: "Read the ranked map",
              body: "Every area is colour-coded by priority and listed in rank order. Filter by signal, click any area for its full Battlecard, and star the ones worth shortlisting.",
            },
            {
              icon: FileDown,
              step: "4",
              title: "Combine, enrich and export",
              body: "Add an AI local area lookup, combine starred areas or the whole catchment into one Battlecard, and export a per-area deck or a combined card as PDF or PowerPoint.",
            },
          ].map((s) => {
            const Icon = s.icon;
            return (
              <li
                key={s.step}
                className="rounded-card border border-neutral-200 p-5"
              >
                <div className="flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-light-accent text-xs font-semibold text-white">
                    {s.step}
                  </span>
                  <Icon size={18} className="text-neutral-400" />
                </div>
                <h3 className="mt-3 text-sm font-semibold">{s.title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-neutral-600">
                  {s.body}
                </p>
              </li>
            );
          })}
        </ol>
      </section>

      {/* Capabilities */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">What you can do</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card icon={Presentation} title="Single-slide Battlecards">
            Each area is one clear slide: key statistics, target audience and
            messaging, the development and location, and charts for age, income
            and tenure. The same payload renders to the web drawer, PDF and
            PowerPoint.
          </Card>
          <Card icon={Target} title="Audience segments">
            Rank a catchment for a specific audience, such as first time buyers,
            growing families or downsizers. The segment retunes the scoring so
            the map reflects who you are actually selling to.
          </Card>
          <Card icon={Ruler} title="Drive time or radius">
            Use a realistic drive-time isochrone, or a straight-line radius where
            drive times are unreliable, such as central London. Both feed the
            same scoring.
          </Card>
          <Card icon={Star} title="Star and combine">
            Star the areas worth pursuing, then export them as a deck of one
            slide per area, or combine them, or the whole catchment, into a
            single aggregate Battlecard for the wider area.
          </Card>
          <Card icon={Sparkles} title="AI local area lookup">
            Add an AI-generated summary of the area and its amenities, transport,
            retail, leisure, schools and healthcare. It shows on the page and is
            included in the matching export. Generations are metered, so external
            users draw on a monthly allowance.
          </Card>
          <Card icon={Palette} title="Builder profiles and branding">
            Save targeting profiles per house builder brand, with their segment,
            product, colours and logo. Picking a profile fills the brief and
            themes every export to that brand.
          </Card>
        </div>
      </section>

      {/* Use cases */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Real-world use cases</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Card icon={Building2} title="Residential new-build">
            For a new housing development, find the areas whose income, tenure
            and age profile fit the price band and bed mix, and tailor the
            message to first-time buyers, second steppers or downsizers by area.
          </Card>
          <Card icon={Dumbbell} title="Leisure centre catchment">
            For a gym or leisure centre, size the addressable population within a
            realistic drive time and prioritise the neighbourhoods most likely to
            convert to memberships.
          </Card>
          <Card icon={Store} title="Retail site selection">
            Compare candidate sites by the quality and scale of the catchment
            each one commands, with the demographics that match the retail
            format.
          </Card>
          <Card icon={Landmark} title="Local authority communications">
            Plan public consultation or service communications around the real
            population an area reaches, with confidence flags where data is thin.
          </Card>
        </div>
      </section>

      {/* Admin note */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">For administrators</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card icon={Users} title="Users and access">
            Runs are private to their owner and anyone they are shared with.
            Admins manage roles, pin external users to a builder group, and set
            each group&apos;s monthly AI allowance.
          </Card>
          <Card icon={ShieldCheck} title="Audit trail">
            Every meaningful action is logged with who, when, what and any cost,
            filterable by user, action, cost and date.
          </Card>
          <Card icon={Layers} title="Reference data status">
            A status indicator shows whether the underlying open datasets are
            fully loaded, with the detailed sources kept to the admin area.
          </Card>
        </div>
      </section>

      <section className="rounded-card border border-neutral-200 p-6 text-center">
        <h2 className="text-lg font-semibold">Ready to try it</h2>
        <p className="mx-auto mt-1 max-w-xl text-sm text-neutral-600">
          Head to the catchment map, paste a postcode and build your first ranked
          catchment.
        </p>
        <a
          href="/"
          className="mt-4 inline-flex items-center gap-2 rounded-card bg-light-accent px-4 py-2 text-sm font-semibold text-white"
        >
          <MapPin size={16} /> Open the catchment map
        </a>
      </section>
    </div>
  );
}
