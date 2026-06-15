import type { Config } from "tailwindcss";

// App shell design tokens from design-framework.md. Two surfaces, two design
// languages: the app shell (Mediaworks and Apple light or dark) lives here.
// Client Battlecard exports carry their own brand via theme config and must
// not draw from these tokens.
const config: Config = {
  darkMode: "class",
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Light mode: Apple-style. The accent is a CSS variable so a client
        // brand can white-label the interface at runtime; the literal is the
        // default when no brand is set (see BrandTheme).
        light: {
          bg: "#F5F5F7",
          accent: "var(--brand-accent, #0071E3)",
        },
        // Dark mode: Mediaworks palette. Same brand override, different default.
        dark: {
          bg: "#0D0D0D",
          accent: "var(--brand-accent, #DC167A)",
        },
        // Semantic colours for priority bands and status. Not arbitrary use.
        priority: {
          high: "#34C759", // green
          mid: "#FF9500", // orange
          low: "#FF3B30", // red
        },
        // LandLynk brand wordmark colours: green "Land", charcoal "Lynk".
        brand: {
          green: "#2F6B3A",
          ink: "#1E2A32",
        },
      },
      fontFamily: {
        // Poppins by default. --brand-font lets a client brand white-label the
        // interface typeface at runtime, falling back to Poppins (see BrandTheme).
        sans: [
          "var(--brand-font, var(--font-poppins))",
          "Poppins",
          "system-ui",
          "sans-serif",
        ],
        output: ["var(--font-poppins)", "Poppins", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "14px",
      },
      transitionTimingFunction: {
        drawer: "cubic-bezier(0.32, 0.72, 0, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
