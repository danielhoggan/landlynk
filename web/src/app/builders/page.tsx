"use client";

import { useCallback, useEffect, useState } from "react";
import { Building2, Plus, Trash2 } from "lucide-react";
import {
  listGroups,
  listBuilders,
  getBuilderProfiles,
  createGroup,
  deleteGroup,
  createBuilder,
  deleteBuilder,
  saveProfile,
  deleteProfile,
  updateGroup,
  uploadBrandLogo,
  type BuilderGroup,
  type Builder,
  type BuilderProfile,
} from "@/lib/client";
import { SEGMENTS } from "@/lib/segments";
import { INDUSTRIES, industryLabel } from "@/lib/industries";
import { useUser } from "@/lib/userContext";

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1] ?? "");
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// Admin-only: manage the builder org model. A group (client) owns brands, each
// brand owns targeting profiles. External users are then pinned to a group on
// the Users page and see only its profiles.
export default function BuildersPage() {
  const { isAdmin, loading } = useUser();
  const [groups, setGroups] = useState<BuilderGroup[]>([]);
  const [builders, setBuilders] = useState<Builder[]>([]);
  const [profiles, setProfiles] = useState<BuilderProfile[]>([]);
  const [newGroup, setNewGroup] = useState("");
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [g, b, p] = await Promise.all([
        listGroups(),
        listBuilders(),
        getBuilderProfiles(),
      ]);
      setGroups(g);
      setBuilders(b);
      setProfiles(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }, []);

  useEffect(() => {
    if (isAdmin) refresh();
  }, [isAdmin, refresh]);

  if (loading) return <p className="p-4 text-sm text-neutral-500">Loading...</p>;
  if (!isAdmin) {
    return (
      <div className="mx-auto max-w-2xl p-4">
        <p className="rounded-card border border-neutral-200 bg-white p-4 text-sm text-neutral-600">
          This page is for admins only.
        </p>
      </div>
    );
  }

  async function addGroup() {
    if (!newGroup.trim()) return;
    await createGroup(newGroup.trim());
    setNewGroup("");
    refresh();
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5 p-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <Building2 size={20} /> Brands
      </h1>
      <p className="text-sm text-neutral-500">
        Groups own brands, brands own targeting profiles. Pin external users to a
        group on the Users page so they only see its profiles.
      </p>
      {error && <p className="text-sm text-priority-low">{error}</p>}

      <div className="flex gap-2">
        <input
          value={newGroup}
          onChange={(e) => setNewGroup(e.target.value)}
          placeholder="New group (e.g. Bellway plc)"
          className="flex-1 rounded-card border border-neutral-300 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={addGroup}
          className="flex items-center gap-1.5 rounded-card bg-light-accent px-3 py-2 text-sm font-semibold text-white"
        >
          <Plus size={16} /> Group
        </button>
      </div>

      {groups.map((g) => (
        <GroupCard
          key={g.id}
          group={g}
          builders={builders.filter((b) => b.groupId === g.id)}
          profiles={profiles}
          onChange={refresh}
        />
      ))}
      {groups.length === 0 && (
        <p className="text-sm text-neutral-500">No groups yet.</p>
      )}
    </div>
  );
}

function GroupCard({
  group,
  builders,
  profiles,
  onChange,
}: {
  group: BuilderGroup;
  builders: Builder[];
  profiles: BuilderProfile[];
  onChange: () => void;
}) {
  const [name, setName] = useState("");
  const [colour, setColour] = useState("#0A1F44");
  const [secondary, setSecondary] = useState("#1F5A3C");
  const [accent, setAccent] = useState("#C9A24B");
  const [fonts, setFonts] = useState("");
  const [brandIndustry, setBrandIndustry] = useState("");
  const [targetLocations, setTargetLocations] = useState("");
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [brandErr, setBrandErr] = useState("");
  const [cap, setCap] = useState(
    group.monthlyCap == null ? "" : String(group.monthlyCap),
  );
  const [savingCap, setSavingCap] = useState(false);

  return (
    <div className="rounded-card border border-neutral-200 bg-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-sm font-semibold">{group.name}</h2>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-1.5 text-xs text-neutral-500">
            Monthly AI cap
            <input
              value={cap}
              onChange={(e) => setCap(e.target.value)}
              placeholder="∞"
              type="number"
              title="Blank means unlimited"
              className="w-20 rounded-card border border-neutral-300 px-2 py-1 text-xs"
            />
          </label>
          <button
            type="button"
            disabled={savingCap}
            onClick={async () => {
              setSavingCap(true);
              try {
                await updateGroup(group.id, {
                  name: group.name,
                  monthlyCap: cap === "" ? null : Number(cap),
                });
                onChange();
              } finally {
                setSavingCap(false);
              }
            }}
            className="rounded-card border border-neutral-300 px-2 py-1 text-xs font-semibold disabled:opacity-50"
          >
            Save
          </button>
          <button
            type="button"
            onClick={async () => {
              await deleteGroup(group.id);
              onChange();
            }}
            className="text-neutral-400 hover:text-priority-low"
            aria-label="Delete group"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <div className="mt-3 space-y-3 pl-3">
        {builders.map((b) => (
          <BrandCard
            key={b.id}
            brand={b}
            profiles={profiles.filter((p) => p.builderId === b.id)}
            onChange={onChange}
          />
        ))}
        <div className="rounded-card border border-dashed border-neutral-300 p-2.5">
          <p className="mb-2 text-xs font-semibold text-neutral-500">New brand</p>
          <div className="flex flex-wrap items-center gap-2">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Brand name (e.g. Bellway)"
              className="flex-1 rounded-card border border-neutral-300 px-3 py-1.5 text-sm"
            />
            <label className="flex items-center gap-1 text-xs text-neutral-500">
              Primary
              <input
                type="color"
                value={colour}
                onChange={(e) => setColour(e.target.value)}
                className="h-8 w-9 rounded border border-neutral-300"
              />
            </label>
            <label className="flex items-center gap-1 text-xs text-neutral-500">
              Secondary
              <input
                type="color"
                value={secondary}
                onChange={(e) => setSecondary(e.target.value)}
                className="h-8 w-9 rounded border border-neutral-300"
              />
            </label>
            <label className="flex items-center gap-1 text-xs text-neutral-500">
              Accent
              <input
                type="color"
                value={accent}
                onChange={(e) => setAccent(e.target.value)}
                className="h-8 w-9 rounded border border-neutral-300"
              />
            </label>
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <input
              value={fonts}
              onChange={(e) => setFonts(e.target.value)}
              placeholder="Web fonts (comma separated)"
              className="flex-1 rounded-card border border-neutral-300 px-3 py-1.5 text-xs"
            />
            <select
              value={brandIndustry}
              onChange={(e) => setBrandIndustry(e.target.value)}
              title="Industry (tailors segments and How it works for this brand)"
              className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs text-neutral-600"
            >
              <option value="">Industry (optional)</option>
              {INDUSTRIES.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.label}
                </option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-xs font-medium text-neutral-600">
              Brand logo (required)
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setLogoFile(e.target.files?.[0] ?? null)}
                className="text-xs font-normal text-neutral-500"
              />
            </label>
            <textarea
              value={targetLocations}
              onChange={(e) => setTargetLocations(e.target.value)}
              placeholder="Best / target locations: postcodes of known-good developments, one per line (optional, used to weight toward similar areas)"
              rows={2}
              className="w-full rounded-card border border-neutral-300 px-3 py-1.5 text-xs"
            />
            <button
              type="button"
              onClick={async () => {
                setBrandErr("");
                if (!name.trim()) return setBrandErr("Name is required.");
                if (!logoFile) return setBrandErr("A logo is required.");
                try {
                  const { id } = await createBuilder({
                    groupId: group.id,
                    name: name.trim(),
                    themeHeading: colour,
                    themeSecondary: secondary,
                    themeAccent: accent,
                    fonts: fonts
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                    targetLocations: targetLocations
                      .split(/[\n,]/)
                      .map((s) => s.trim())
                      .filter(Boolean),
                    industry: brandIndustry || null,
                  });
                  const base64 = await fileToBase64(logoFile);
                  await uploadBrandLogo(id, logoFile.name, base64);
                  setName("");
                  setFonts("");
                  setBrandIndustry("");
                  setTargetLocations("");
                  setLogoFile(null);
                  onChange();
                } catch (e) {
                  setBrandErr(
                    e instanceof Error ? e.message : "Could not create brand",
                  );
                }
              }}
              className="flex items-center gap-1.5 rounded-card bg-light-accent px-3 py-1.5 text-sm font-semibold text-white"
            >
              <Plus size={14} /> Brand
            </button>
          </div>
          {brandErr && (
            <p className="mt-1 text-xs text-priority-low">{brandErr}</p>
          )}
        </div>
      </div>
    </div>
  );
}

function BrandCard({
  brand,
  profiles,
  onChange,
}: {
  brand: Builder;
  profiles: BuilderProfile[];
  onChange: () => void;
}) {
  const [form, setForm] = useState({
    name: "",
    segment: "",
    bedRange: "",
    priceFrom: "",
    priceTo: "",
    strapline: "",
  });
  const set = (k: keyof typeof form, v: string) =>
    setForm((f) => ({ ...f, [k]: v }));

  return (
    <div className="rounded-card border border-neutral-200 p-3">
      <div className="flex items-center gap-2">
        {brand.logoPath ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={`/api/builders/${brand.id}/logo`}
            alt={`${brand.name} logo`}
            className="h-5 w-auto max-w-[60px] object-contain"
          />
        ) : (
          <span
            className="inline-block h-3 w-3 rounded-full"
            style={{ backgroundColor: brand.themeHeading }}
          />
        )}
        {[brand.themeHeading, brand.themeSecondary, brand.themeAccent]
          .filter(Boolean)
          .map((c, i) => (
            <span
              key={i}
              className="inline-block h-3 w-3 rounded-full border border-neutral-200"
              style={{ backgroundColor: c as string }}
            />
          ))}
        <span className="text-sm font-semibold">{brand.name}</span>
        {brand.industry && (
          <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] font-semibold text-neutral-500">
            {industryLabel(brand.industry) ?? brand.industry}
          </span>
        )}
        <button
          type="button"
          onClick={async () => {
            await deleteBuilder(brand.id);
            onChange();
          }}
          className="ml-auto text-neutral-400 hover:text-priority-low"
          aria-label="Delete brand"
        >
          <Trash2 size={14} />
        </button>
      </div>

      <ul className="mt-2 space-y-1">
        {profiles.map((p) => (
          <li
            key={p.id}
            className="flex items-center justify-between rounded bg-neutral-50 px-2 py-1 text-xs"
          >
            <span>
              <span className="font-semibold">{p.name}</span>
              {p.segment ? ` · ${p.segment}` : ""}
              {p.bedRange ? ` · ${p.bedRange} bed` : ""}
            </span>
            <button
              type="button"
              onClick={async () => {
                await deleteProfile(p.id);
                onChange();
              }}
              className="text-neutral-400 hover:text-priority-low"
              aria-label="Delete profile"
            >
              <Trash2 size={12} />
            </button>
          </li>
        ))}
      </ul>

      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <input
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          placeholder="Profile name"
          className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs"
        />
        <select
          value={form.segment}
          onChange={(e) => set("segment", e.target.value)}
          className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs"
        >
          <option value="">Segment (optional)</option>
          {SEGMENTS.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
        <input
          value={form.bedRange}
          onChange={(e) => set("bedRange", e.target.value)}
          placeholder="Bed range (e.g. 3 to 4)"
          className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs"
        />
        <input
          value={form.strapline}
          onChange={(e) => set("strapline", e.target.value)}
          placeholder="Strapline"
          className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs"
        />
        <input
          value={form.priceFrom}
          onChange={(e) => set("priceFrom", e.target.value)}
          placeholder="Price from"
          type="number"
          className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs"
        />
        <input
          value={form.priceTo}
          onChange={(e) => set("priceTo", e.target.value)}
          placeholder="Price to"
          type="number"
          className="rounded-card border border-neutral-300 px-2 py-1.5 text-xs"
        />
      </div>
      <button
        type="button"
        onClick={async () => {
          if (!form.name.trim()) return;
          await saveProfile({
            builderId: brand.id,
            name: form.name.trim(),
            segment: form.segment || null,
            bedRange: form.bedRange || null,
            priceFrom: form.priceFrom ? Number(form.priceFrom) : null,
            priceTo: form.priceTo ? Number(form.priceTo) : null,
            strapline: form.strapline || null,
          });
          setForm({
            name: "",
            segment: "",
            bedRange: "",
            priceFrom: "",
            priceTo: "",
            strapline: "",
          });
          onChange();
        }}
        className="mt-2 flex items-center gap-1.5 rounded-card border border-neutral-300 px-3 py-1.5 text-xs font-semibold"
      >
        <Plus size={14} /> Add profile
      </button>
    </div>
  );
}
