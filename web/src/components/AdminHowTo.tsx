"use client";

import { Users, ShieldCheck, Layers, type LucideIcon } from "lucide-react";
import { useUser } from "@/lib/userContext";

function Card({
  icon: Icon,
  title,
  children,
}: {
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-card border border-neutral-200 p-5">
      <Icon size={22} className="text-light-accent" />
      <h3 className="mt-3 text-sm font-semibold">{title}</h3>
      <p className="mt-1 text-sm leading-relaxed text-neutral-600">{children}</p>
    </div>
  );
}

// The admin-only capabilities block on the How it works page. Hidden entirely
// from non-admins, since those features are not available to them.
export function AdminHowTo() {
  const { isAdmin } = useUser();
  if (!isAdmin) return null;
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold">For administrators</h2>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card icon={Users} title="Users and access">
          Runs are private to their owner and anyone they are shared with. Admins
          manage roles, pin external users to a builder group, and set each
          group&apos;s monthly AI allowance.
        </Card>
        <Card icon={ShieldCheck} title="Audit trail">
          Every meaningful action is logged with who, when, what and any cost,
          filterable by user, action, cost and date.
        </Card>
        <Card icon={Layers} title="Reference data status">
          A status indicator shows whether the underlying open datasets are fully
          loaded, with the detailed sources kept to the admin area.
        </Card>
      </div>
    </section>
  );
}
