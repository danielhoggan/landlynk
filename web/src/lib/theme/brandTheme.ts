// Brand theming for client-facing Battlecard exports. The same render takes any
// theme config. Never hard-code a client brand into render logic
// (design-framework.md, house-standards.md). The app shell is unaffected by
// these themes; it uses the Mediaworks and Apple light or dark systems.

export interface BrandTheme {
  id: string;
  name: string;
  colors: {
    primary: string;
    secondary: string;
    accent: string;
  };
  /** Logo URL or path, resolved at render time. */
  logo: string | null;
  fonts: {
    /** Document font for PDF and PPTX. Poppins for now. */
    document: string;
    /** HTML font for web output. Poppins for now. */
    web: string;
  };
}

/**
 * Default theme used when a client brand does not override. Headings fall back
 * to the LandLynk green per the output conventions (house-standards.md).
 */
export const DEFAULT_THEME: BrandTheme = {
  id: "landlynk-default",
  name: "LandLynk Default",
  colors: {
    primary: "#2F6B3A", // LandLynk green, default document heading colour
    secondary: "#0D0D0D",
    accent: "#DC167A",
  },
  logo: null,
  fonts: {
    document: "Poppins",
    web: "Poppins",
  },
};

/**
 * Reference theme from the Abbots Vale Battlecard: Hopkins Homes navy with a
 * gold accent. This is a theme, not a default.
 */
export const HOPKINS_THEME: BrandTheme = {
  id: "hopkins-homes",
  name: "Hopkins Homes",
  colors: {
    primary: "#0A1F44", // navy header
    secondary: "#1B2A4A",
    accent: "#C9A24B", // gold / amber accent
  },
  logo: null,
  fonts: {
    document: "Poppins",
    web: "Poppins",
  },
};
