import { MapPin } from "lucide-react";

interface LogoProps {
  /** Tailwind text-size class controls the overall scale, e.g. "text-xl". */
  className?: string;
  /** Hide the pin mark when space is tight. */
  showMark?: boolean;
}

// The LandLynk wordmark, recreated as scalable, theme-aware markup: green
// "Land", charcoal "Lynk" (light in dark mode), with the map-pin motif. To use
// the exact supplied raster instead, drop it at web/public/logo.png and swap
// this component's body for an <img>.
export function Logo({ className = "text-lg", showMark = true }: LogoProps) {
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
