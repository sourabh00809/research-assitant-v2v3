"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { api, postApi } from "../../lib/api";
import { useSession } from "../../components/AuthProvider";
import { Panel, LoadingSpinner } from "../../components/ui";
import SidebarLayout from "../../components/SidebarLayout";

interface CheckoutResponse { url: string }
interface Plan { tier: string; name: string; desc: string; price: string }

export default function BillingPage() {
  const router = useRouter();
  const { session } = useSession();
  const { data: plans, isLoading } = useSWR<Plan[]>("/api/v1/billing/plans", api);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");

  async function startCheckout(tier: string) {
    if (!session?.team?.id) return;
    setBusy(tier);
    try {
      const checkout = await postApi<CheckoutResponse>("/api/v1/billing/checkout", {
        team_id: session.team.id, tier,
        success_url: window.location.href, cancel_url: window.location.href,
      });
      setMessage(`Checkout URL: ${checkout.url}`);
    } catch {
      setMessage("Billing not available in dev mode.");
    }
    setBusy("");
  }

  if (!session?.authenticated) { router.replace("/login"); return null; }

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
        <h1 className="text-3xl font-bold">Billing & Usage</h1>
        <p className="mt-1 text-sm text-slate-600">Manage your subscription tier.</p>

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
                  disabled={busy === plan.tier}
                  onClick={() => startCheckout(plan.tier)}
                >
                  {busy === plan.tier ? "Processing..." : `Subscribe ${plan.name}`}
                </button>
              </Panel>
            ))}
          </div>
        )}
      </div>
    </SidebarLayout>
  );
}
