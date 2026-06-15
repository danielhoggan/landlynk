"use client";

import { MapPin } from "lucide-react";
import { useUser } from "@/lib/userContext";

interface LogoProps {
  /** Tailwind text-size class controls the overall scale, e.g. "text-xl". */
  className?: string;
  /** Hide the pin mark when space is tight. */
  showMark?: boolean;
}

// The app wordmark. For a signed-in user whose group has a brand logo, render
// that logo (white-labelling the interface); otherwise the LandLynk wordmark:
// green "Land", charcoal "Lynk" (light in dark mode), with the map-pin motif.
export function Logo({ className = "text-lg", showMark = true }: LogoProps) {
  const { user } = useUser();
  const brand = user?.brand;

  if (brand?.hasLogo) {
    return (
      <span className={`inline-flex items-center ${className}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`/api/builders/${brand.builderId}/logo`}
          alt={`${brand.name} logo`}
          className="w-auto max-w-[160px] object-contain"
          style={{ height: "1.6em" }}
        />
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 font-semibold tracking-tight ${className}`}
    >
      {showMark && (
        <MapPin
          className="text-brand-green"
          fill="currentColor"
          size="1em"
          aria-hidden
        />
      )}
      <span>
        <span className="text-brand-green">Land</span>
        <span className="text-brand-ink">Lynk</span>
      </span>
    </span>
  );
}
