"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { useAuth, useUser } from "@clerk/nextjs";
import { api, postApi } from "../../lib/api";
import { Panel, LoadingSpinner } from "../../components/ui";
import { PaymentModal } from "../../components/PaymentModal";
import SidebarLayout from "../../components/SidebarLayout";

interface Plan { tier: string; name: string; desc: string; price: string }

export default function BillingPage() {
  const router = useRouter();
  const { user } = useUser();
  const { isLoaded, isSignedIn } = useAuth();
  const { data: plans, isLoading } = useSWR<Plan[]>("/api/v1/billing/plans", api);
  const [selected, setSelected] = useState<Plan | null>(null);
  const [message, setMessage] = useState("");
  const [currentTier, setCurrentTier] = useState("free");

  if (!isLoaded) return <LoadingSpinner text="Loading..." />;
  if (!isSignedIn) { router.replace("/login"); return null; }

  async function handleUpgrade() {
    if (!selected) return;
    try {
      await postApi("/api/v1/billing/upgrade", { tier: selected.tier });
      setMessage(`Successfully upgraded to ${selected.name}!`);
      setCurrentTier(selected.tier);
    } catch {
      setMessage("Upgrade failed. Please try again.");
    }
    setSelected(null);
  }

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold">Billing & Usage</h1>
        <p className="mt-1 text-sm text-slate-600">Choose your subscription tier.</p>

        {message && (
          <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">
            {message}
          </div>
        )}

        {isLoading ? <LoadingSpinner text="Loading plans..." /> : (
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {plans?.map((plan) => (
              <Panel key={plan.tier} title={plan.name} meta={plan.price}>
                <p className="text-sm text-slate-600">{plan.desc}</p>
                <button
                  className="mt-4 w-full rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
                  disabled={currentTier === plan.tier}
                  onClick={() => setSelected(plan)}
                >
                  {currentTier === plan.tier ? "Current Plan" : `Subscribe ${plan.name}`}
                </button>
              </Panel>
            ))}
          </div>
        )}

        {selected && (
          <PaymentModal
            tier={selected.tier}
            price={selected.price}
            name={selected.name}
            onSuccess={handleUpgrade}
            onCancel={() => setSelected(null)}
          />
        )}
      </div>
    </SidebarLayout>
  );
}
