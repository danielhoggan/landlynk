import type { Metadata } from "next";
import { Inter, Tenor_Sans } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";
import { AppShell } from "@/components/shell/AppShell";

// App UI font: Inter. Web output font: Tenor Sans (design-framework.md).
const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const tenorSans = Tenor_Sans({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-tenor-sans",
});

export const metadata: Metadata = {
  title: "LandLynk",
  description:
    "The Geographic Intelligence Engine. Ranked, clickable catchment maps with auto-generated Battlecards.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en-GB" className={`${inter.variable} ${tenorSans.variable}`}>
      <body>
        <Providers>
          <AppShell>{children}</AppShell>
        </Providers>
      </body>
    </html>
  );
}
