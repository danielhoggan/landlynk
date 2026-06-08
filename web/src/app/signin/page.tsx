"use client";

import { signIn } from "next-auth/react";
import { LogIn } from "lucide-react";
import { Logo } from "@/components/shell/Logo";

// Sign-in surface. SSO is the only auth path; there is no local password flow
// (house-standards.md). The single action starts the Azure AD flow.
export default function SignInPage() {
  return (
    <div className="flex min-h-[70vh] items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-card border border-neutral-200 p-8 text-center dark:border-neutral-800">
        <Logo className="justify-center text-2xl" />
        <p className="mt-2 text-sm text-neutral-500">
          Sign in with your work account to continue.
        </p>
        <button
          type="button"
          onClick={() => signIn("azure-ad", { callbackUrl: "/" })}
          className="mt-6 flex w-full items-center justify-center gap-2 rounded-card bg-light-accent py-2.5 text-sm font-semibold text-white dark:bg-dark-accent"
        >
          <LogIn size={16} /> Sign in with Microsoft
        </button>
      </div>
    </div>
  );
}
