import {
  Map,
  Compass,
  Database,
  Settings,
  History,
  Archive,
  Users,
  Sparkles,
  Building2,
  ScrollText,
  PoundSterling,
  type LucideIcon,
} from "lucide-react";

export type NavSectionId = "catchments" | "info" | "admin";

export interface NavItem {
  label: string;
  icon: LucideIcon;
  href: string;
  section: NavSectionId;
  /** Shown only to admins. */
  adminOnly?: boolean;
}

// Single source for the nav, shared by the desktop sidebar and the mobile
// drawer. Grouped into sections (Catchments, Info, Admin) so a user reads "/"
// as starting a new run, with past runs and help grouped under clear headings.
// Battlecards are reached inside a catchment, so not a top-level item.
export const NAV_ITEMS: NavItem[] = [
  { label: "New catchment", icon: Map, href: "/", section: "catchments" },
  { label: "History", icon: History, href: "/history", section: "catchments" },
  { label: "Archived", icon: Archive, href: "/archived", section: "catchments" },
  { label: "How it works", icon: Compass, href: "/how-it-works", section: "info" },
  { label: "Settings", icon: Settings, href: "/settings", section: "info" },
  { label: "Reference data", icon: Database, href: "/data", section: "admin", adminOnly: true },
  { label: "Users", icon: Users, href: "/users", section: "admin", adminOnly: true },
  { label: "Brands", icon: Building2, href: "/builders", section: "admin", adminOnly: true },
  { label: "AI models", icon: Sparkles, href: "/models", section: "admin", adminOnly: true },
  { label: "Audits", icon: ScrollText, href: "/audit", section: "admin", adminOnly: true },
  { label: "Costs", icon: PoundSterling, href: "/costs", section: "admin", adminOnly: true },
];

// Section order and headings, rendered as uppercase subheadings in the nav.
const NAV_SECTIONS: { id: NavSectionId; heading: string }[] = [
  { id: "catchments", heading: "Catchments" },
  { id: "info", heading: "Info" },
  { id: "admin", heading: "Admin" },
];

/** The nav grouped into sections, hiding admin-only items from non-admins and
 * dropping any section left with no visible items. */
export function navSections(
  isAdmin: boolean,
): { id: NavSectionId; heading: string; items: NavItem[] }[] {
  return NAV_SECTIONS.map((section) => ({
    ...section,
    items: NAV_ITEMS.filter(
      (i) => i.section === section.id && (isAdmin || !i.adminOnly),
    ),
  })).filter((section) => section.items.length > 0);
}

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}
