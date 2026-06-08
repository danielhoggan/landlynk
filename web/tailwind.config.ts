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
        // Light mode: Apple-style.
        light: {
          bg: "#F5F5F7",
          accent: "#0071E3",
        },
        // Dark mode: Mediaworks palette.
        dark: {
          bg: "#0D0D0D",
          accent: "#DC167A",
        },
        // Semantic colours for priority bands and status. Not arbitrary use.
        priority: {
          high: "#34C759", // green
          mid: "#FF9500", // orange
          low: "#FF3B30", // red
        },
      },
      fontFamily: {
        // App UI font: Inter. Web output font: Tenor Sans.
        sans: ["Inter", "system-ui", "sans-serif"],
        output: ["'Tenor Sans'", "Georgia", "serif"],
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
