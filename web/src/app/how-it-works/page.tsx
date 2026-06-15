import type { Metadata } from "next";
import { HowItWorks } from "@/components/HowItWorks";

export const metadata: Metadata = {
  title: "How it works - LandLynk",
};

// Tailors to the signed-in user's industry and company (see HowItWorks). Cards
// follow the design framework: 14px radius, 1px borders, no shadow.
export default function HowItWorksPage() {
  return <HowItWorks />;
}
