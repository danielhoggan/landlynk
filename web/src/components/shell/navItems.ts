import {
  Map,
  Compass,
  Database,
  Settings,
  History,
  Archive,
  Users,
  Sparkles,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  icon: LucideIcon;
  href: string;
  /** Shown only to admins. */
  adminOnly?: boolean;
}

// Single source for the nav, shared by the desktop sidebar and the mobile
// drawer. Battlecards are reached inside a catchment, so not a top-level item.
export const NAV_ITEMS: NavItem[] = [
  { label: "Catchment map", icon: Map, href: "/" },
  { label: "How it works", icon: Compass, href: "/how-it-works" },
  { label: "History", icon: History, href: "/history" },
  { label: "Archived", icon: Archive, href: "/archived" },
  { label: "Reference data", icon: Database, href: "/data" },
  { label: "Users", icon: Users, href: "/users", adminOnly: true },
  { label: "AI models", icon: Sparkles, href: "/models", adminOnly: true },
  { label: "Settings", icon: Settings, href: "/settings" },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}
