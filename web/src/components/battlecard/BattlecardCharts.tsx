"use client";

import type {
  AgeBand,
  BattlecardCharts as Charts,
  DataValue,
  IncomeChart,
  TenureChart,
} from "@/lib/types/battlecard";
import { fmtCurrency, fmtPercent } from "@/lib/format";

// The three Battlecard charts from the Abbots Vale visual summary: age
// demographics (banded bar), household income (bar with callouts) and housing
// tenure (donut). Each pairs colour with a text label and value so it never
// relies on colour alone (design-framework.md, accessibility).

const num = (dv: DataValue): number => (dv.value === null ? 0 : dv.value);

export function BattlecardCharts({ charts }: { charts: Charts }) {
  return (
    <div className="space-y-5">
      <AgeBarChart bands={charts.ageDemographics} />
      <IncomeBarChart income={charts.householdIncome} />
      <TenureDonut tenure={charts.housingTenure} />
    </div>
  );
}

function ChartFrame({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-card border border-neutral-200 p-4">
      <h3 className="mb-3 text-sm font-semibold">{title}</h3>
      {children}
    </section>
  );
}

function AgeBarChart({ bands }: { bands: AgeBand[] }) {
  const max = Math.max(1, ...bands.map((b) => num(b.percentage)));
  return (
    <ChartFrame title="Age demographics">
      <ul className="space-y-2">
        {bands.map((band) => (
          <li
            key={band.label}
            className="grid grid-cols-[5rem_1fr_3rem] items-center gap-2"
          >
            <span className="text-xs text-neutral-500">{band.label}</span>
            <span className="h-3 rounded-full bg-neutral-100">
              <span
                className="block h-3 rounded-full bg-light-accent"
                style={{ width: `${(num(band.percentage) / max) * 100}%` }}
              />
            </span>
            <span className="text-right text-xs font-semibold tabular-nums">
              {fmtPercent(band.percentage)}
            </span>
          </li>
        ))}
      </ul>
    </ChartFrame>
  );
}

function IncomeBarChart({ income }: { income: IncomeChart }) {
  const max = Math.max(
    1,
    num(income.mean),
    num(income.median),
    num(income.highestLa.value),
  );
  return (
    <ChartFrame title="Household income">
      <div className="space-y-2">
        <IncomeBar label="Mean" dv={income.mean} max={max} />
        <IncomeBar label="Median" dv={income.median} max={max} />
      </div>
      <div className="mt-3 grid grid-cols-2 gap-2 border-t border-neutral-200 pt-3">
        <Callout
          label={`Lowest LA: ${income.lowestLa.name}`}
          dv={income.lowestLa.value}
        />
        <Callout
          label={`Highest LA: ${income.highestLa.name}`}
          dv={income.highestLa.value}
        />
      </div>
    </ChartFrame>
  );
}

function IncomeBar({
  label,
  dv,
  max,
}: {
  label: string;
  dv: DataValue;
  max: number;
}) {
  return (
    <div className="grid grid-cols-[4rem_1fr_5rem] items-center gap-2">
      <span className="text-xs text-neutral-500">{label}</span>
      <span className="h-3 rounded-full bg-neutral-100">
        <span
          className="block h-3 rounded-full bg-light-accent"
          style={{ width: `${(num(dv) / max) * 100}%` }}
        />
      </span>
      <span className="text-right text-xs font-semibold tabular-nums">
        {fmtCurrency(dv)}
      </span>
    </div>
  );
}

function Callout({ label, dv }: { label: string; dv: DataValue }) {
  return (
    <div className="rounded-card bg-neutral-50 p-2">
      <p className="text-[11px] text-neutral-500">{label}</p>
      <p className="text-sm font-semibold">{fmtCurrency(dv)}</p>
    </div>
  );
}

// Categorical, accessible palette for the four tenure segments. Each is labelled
// with its value in the legend, so colour is never the only signal.
const TENURE_COLORS = ["#0071E3", "#34C759", "#FF9500", "#8E8E93"];

function TenureDonut({ tenure }: { tenure: TenureChart }) {
  const segments = [
    { label: "Owns outright", dv: tenure.ownsOutright },
    { label: "Owns with mortgage", dv: tenure.ownsWithMortgage },
    { label: "Social rented", dv: tenure.socialRented },
    { label: "Private rented", dv: tenure.privateRented },
  ];
  const total = segments.reduce((sum, s) => sum + num(s.dv), 0) || 1;

  // Build conic-gradient stops for the donut.
  let acc = 0;
  const stops = segments
    .map((s, i) => {
      const start = (acc / total) * 100;
      acc += num(s.dv);
      const end = (acc / total) * 100;
      return `${TENURE_COLORS[i]} ${start}% ${end}%`;
    })
    .join(", ");

  return (
    <ChartFrame title="Housing tenure">
      <div className="flex items-center gap-4">
        <div
          className="relative h-24 w-24 shrink-0 rounded-full"
          style={{ background: `conic-gradient(${stops})` }}
          role="img"
          aria-label="Housing tenure breakdown"
        >
          <div className="absolute inset-[18%] rounded-full bg-white" />
        </div>
        <ul className="flex-1 space-y-1">
          {segments.map((s, i) => (
            <li key={s.label} className="flex items-center gap-2 text-xs">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-sm"
                style={{ backgroundColor: TENURE_COLORS[i] }}
              />
              <span className="flex-1">{s.label}</span>
              <span className="font-semibold tabular-nums">
                {fmtPercent(s.dv)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </ChartFrame>
  );
}
