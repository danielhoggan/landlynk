import {
  Map,
  Compass,
  Database,
  Settings,
  History,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  label: string;
  icon: LucideIcon;
  href: string;
}

// Single source for the nav, shared by the desktop sidebar and the mobile
// drawer. Battlecards are reached inside a catchment, so not a top-level item.
export const NAV_ITEMS: NavItem[] = [
  { label: "Catchment map", icon: Map, href: "/" },
  { label: "How it works", icon: Compass, href: "/how-it-works" },
  { label: "History", icon: History, href: "/history" },
  { label: "Reference data", icon: Database, href: "/data" },
  { label: "Settings", icon: Settings, href: "/settings" },
];

export function isActive(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname.startsWith(href);
}
