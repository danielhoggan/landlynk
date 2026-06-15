"use client";

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
  GraduationCap,
  HeartPulse,
  ShieldCheck,
  Scale,
  Gauge,
  Ruler,
  Star,
  Sparkles,
  Palette,
  Presentation,
  type LucideIcon,
} from "lucide-react";
import { AdminHowTo } from "@/components/AdminHowTo";
import { useUser } from "@/lib/userContext";
import { industryLabel } from "@/lib/industries";

// Explainer page: what the tool does, its value, the user flow and use cases.
// The hero and use cases are tailored to the signed-in user's industry and
// company when their group has one set; otherwise the generic version shows.

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

interface UseCase {
  icon: LucideIcon;
  title: string;
  body: string;
}
interface Tailored {
  title: string;
  intro: (company: string) => string;
  useCases: UseCase[];
}

// Per-industry hero and use cases. The generic version (no industry) keeps the
// original cross-sector framing.
const GENERIC: Tailored = {
  title: "Turn a location into a targeting strategy",
  intro: (company) =>
    `Paste a postcode or an OS grid reference. ${company} builds a catchment, by drive time or by radius, scores and ranks every area inside it on how worth targeting it is, and generates a Battlecard for each one that says who to target, how to price and what to say. It is built on open public data, so every ranking is reproducible and explainable.`,
  useCases: [
    {
      icon: Building2,
      title: "Residential new-build",
      body: "For a new housing development, find the areas whose income, tenure and age profile fit the price band and bed mix, and tailor the message to first-time buyers, second steppers or downsizers by area.",
    },
    {
      icon: Dumbbell,
      title: "Leisure centre catchment",
      body: "For a gym or leisure centre, size the addressable population within a realistic drive time and prioritise the neighbourhoods most likely to convert to memberships.",
    },
    {
      icon: Store,
      title: "Retail site selection",
      body: "Compare candidate sites by the quality and scale of the catchment each one commands, with the demographics that match the retail format.",
    },
    {
      icon: Landmark,
      title: "Local authority communications",
      body: "Plan public consultation or service communications around the real population an area reaches, with confidence flags where data is thin.",
    },
  ],
};

const BY_INDUSTRY: Record<string, Tailored> = {
  residential: {
    title: "Turn a site into a sales and marketing strategy",
    intro: (company) =>
      `Paste a development postcode or an OS grid reference. ${company} builds a catchment by drive time or radius, scores and ranks every area on how worth targeting it is, and generates a Battlecard per area that says who to target, how to price and what to say.`,
    useCases: [
      {
        icon: Building2,
        title: "New-build launch",
        body: "Find the areas whose income, tenure and age profile fit the price band and bed mix, and rank them so launch spend goes where demand is strongest.",
      },
      {
        icon: Target,
        title: "Pricing and product mix",
        body: "See which audiences each area skews towards, from first-time buyers to downsizers, to sense-check the price band and bed mix for the scheme.",
      },
      {
        icon: Presentation,
        title: "Phasing and messaging",
        body: "Tailor the message area by area and phase release around the neighbourhoods most likely to reserve early.",
      },
    ],
  },
  retail: {
    title: "Choose sites and catchments backed by real demographics",
    intro: (company) =>
      `Paste a candidate location as a postcode or OS grid reference. ${company} sizes the catchment by drive time or radius, scores and ranks the areas inside it, and shows the demographics that match your format.`,
    useCases: [
      {
        icon: Store,
        title: "Site selection",
        body: "Compare candidate sites by the quality and scale of the catchment each one commands, not just by passing footfall.",
      },
      {
        icon: Target,
        title: "Format fit",
        body: "Check the income, age and tenure profile of a catchment against the format you plan to trade, before you commit to a lease.",
      },
      {
        icon: Sparkles,
        title: "Local marketing",
        body: "Prioritise the neighbourhoods around a store for local campaigns and rank them by how well they fit your customer.",
      },
    ],
  },
  leisure: {
    title: "Size the catchment for a new club or venue",
    intro: (company) =>
      `Paste a site postcode or OS grid reference. ${company} builds a realistic drive-time catchment, scores and ranks the areas inside it, and surfaces the neighbourhoods most likely to convert.`,
    useCases: [
      {
        icon: Dumbbell,
        title: "Membership potential",
        body: "Size the addressable population within a realistic drive time and rank areas by how likely they are to convert to memberships.",
      },
      {
        icon: Ruler,
        title: "Drive-time reach",
        body: "Use a true drive-time isochrone so the catchment reflects how members actually travel, not a flat radius.",
      },
      {
        icon: Target,
        title: "Targeted acquisition",
        body: "Focus acquisition spend on the highest-fit neighbourhoods and tailor the offer to each area's profile.",
      },
    ],
  },
  healthcare: {
    title: "Plan services around the population they actually reach",
    intro: (company) =>
      `Paste a site postcode or OS grid reference. ${company} builds a catchment by drive time or radius, ranks the areas inside it, and shows the population profile each service reaches.`,
    useCases: [
      {
        icon: HeartPulse,
        title: "Service planning",
        body: "Understand the size and profile of the population a site reaches, to plan provision and capacity around real demand.",
      },
      {
        icon: Ruler,
        title: "Accessibility",
        body: "Use realistic drive times to see who can actually reach a service, and where access is thin.",
      },
      {
        icon: Scale,
        title: "Demand by area",
        body: "Rank the neighbourhoods in a catchment by their demographic profile to target outreach where it is needed most.",
      },
    ],
  },
  education: {
    title: "Understand the catchment your provision draws from",
    intro: (company) =>
      `Paste a site postcode or OS grid reference. ${company} builds a travel-time catchment, ranks the areas inside it, and shows the demographics of the population it draws from.`,
    useCases: [
      {
        icon: GraduationCap,
        title: "Demand and places",
        body: "Size the population a site draws from and read its age and family profile to plan provision and places.",
      },
      {
        icon: Ruler,
        title: "Travel-to-learn",
        body: "Use realistic travel times to map the true catchment rather than a flat radius.",
      },
      {
        icon: Target,
        title: "Outreach",
        body: "Rank the neighbourhoods in the catchment to focus recruitment and outreach where it will land best.",
      },
    ],
  },
  public_sector: {
    title: "Plan around the real population an area reaches",
    intro: (company) =>
      `Paste a postcode or OS grid reference. ${company} builds a catchment by drive time or radius, ranks the areas inside it, and grounds every figure in open ONS data with confidence flags where data is thin.`,
    useCases: [
      {
        icon: Landmark,
        title: "Consultation reach",
        body: "Plan public consultation around the real population an area reaches, ranked so engagement effort is well placed.",
      },
      {
        icon: Sparkles,
        title: "Service communications",
        body: "Target service communications by the demographic profile of each neighbourhood in the catchment.",
      },
      {
        icon: ShieldCheck,
        title: "Confidence flags",
        body: "Every figure traces to open ONS data, with flags where a small population makes a number less certain.",
      },
    ],
  },
};

export function HowItWorks() {
  const { user } = useUser();
  const industry = user?.brand?.industry ?? null;
  const company = user?.brand?.companyName ?? null;
  const content = (industry && BY_INDUSTRY[industry]) || GENERIC;
  const eyebrow =
    industryLabel(industry) ?? "The Geographic Intelligence Engine";
  const companyWord = company ?? "LandLynk";

  return (
    <div className="mx-auto max-w-5xl space-y-12 p-4 py-8">
      {/* Hero */}
      <header className="max-w-3xl">
        <p className="text-sm font-semibold uppercase tracking-wide text-light-accent">
          {eyebrow}
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight">
          {content.title}
        </h1>
        <p className="mt-3 text-base leading-relaxed text-neutral-600">
          {content.intro(companyWord)}
        </p>
      </header>

      {/* Purpose and value */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Why it exists</h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card icon={Target} title="Evidence, not assumption">
            Marketing strategy for a place is too often built on a hunch. It is
            grounded here in ONS Census and income data for the actual catchment.
          </Card>
          <Card icon={Gauge} title="Seconds, not hours">
            Defining a catchment by eye used to take 15 to 30 minutes per site.
            Here it is an automated sub-second lookup, repeatable at scale.
          </Card>
          <Card icon={Scale} title="Ranked priorities">
            Areas are scored and ordered, so you see where to focus spend and
            effort first rather than reading a flat colour map.
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
            themed to the brand, plus a Google Earth KML of the catchment.
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
              body: "Paste a postcode or OS grid reference. Pick a saved profile to fill the brief in one click, or set the scheme, price band and a target audience segment yourself.",
            },
            {
              icon: Route,
              step: "2",
              title: "Choose the catchment",
              body: "Build a 30-minute drive-time zone, or switch to a straight radius for dense cities. The areas inside it are found and weighted by how much of each falls in the zone.",
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
            messaging, the location, and charts for age, income and tenure. The
            same payload renders to the web drawer, PDF and PowerPoint.
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
            single aggregate Battlecard.
          </Card>
          <Card icon={Sparkles} title="AI local area lookup">
            Add an AI-generated summary of the area and its amenities, transport,
            retail, leisure, schools and healthcare. It shows on the page and is
            included in the matching export. Generations are metered, so external
            users draw on a monthly allowance.
          </Card>
          <Card icon={Palette} title="Saved profiles and branding">
            Save targeting profiles per brand, with their segment, product,
            colours and logo. Picking a profile fills the brief and themes every
            export to that brand.
          </Card>
        </div>
      </section>

      {/* Use cases, tailored to the industry */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">
          {industry ? "What it means for you" : "Real-world use cases"}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {content.useCases.map((u) => (
            <Card key={u.title} icon={u.icon} title={u.title}>
              {u.body}
            </Card>
          ))}
        </div>
      </section>

      {/* Admin note, shown to admins only */}
      <AdminHowTo />

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
