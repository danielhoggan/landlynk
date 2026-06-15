"use client";

import { useEffect } from "react";
import { useUser } from "@/lib/userContext";

// White-labels the app interface for a signed-in user whose group has a brand.
// The brand comes from /me; users without a group keep the default
// Mediaworks/Apple theme. Colours and the typeface are exposed as CSS variables
// that the Tailwind tokens consume (see tailwind.config.ts); the logo is handled
// by <Logo>. Renders nothing.
export function BrandTheme() {
  const { activeBrand } = useUser();
  // The interface accent is the brand's accent, falling back to its heading
  // colour so a brand that only set a primary colour still tints the shell.
  const accent = activeBrand?.themeAccent ?? activeBrand?.themeHeading ?? null;
  const font = activeBrand?.fonts?.[0]?.trim() || null;

  useEffect(() => {
    const root = document.documentElement;
    if (accent) root.style.setProperty("--brand-accent", accent);
    else root.style.removeProperty("--brand-accent");
    return () => {
      root.style.removeProperty("--brand-accent");
    };
  }, [accent]);

  useEffect(() => {
    const root = document.documentElement;
    if (!font) {
      root.style.removeProperty("--brand-font");
      return;
    }
    root.style.setProperty("--brand-font", `"${font}"`);
    // Pull the typeface from Google Fonts if it is one. Harmless if the name is
    // not a Google font: the link 404s and the family falls back to Poppins.
    const link = document.createElement("link");
    link.rel = "stylesheet";
    const family = encodeURIComponent(font).replace(/%20/g, "+");
    link.href = `https://fonts.googleapis.com/css2?family=${family}:wght@400;500;600;700&display=swap`;
    document.head.appendChild(link);
    return () => {
      root.style.removeProperty("--brand-font");
      link.remove();
    };
  }, [font]);

  return null;
}
