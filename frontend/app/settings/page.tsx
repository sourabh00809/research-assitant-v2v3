"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { postApi } from "../../lib/api";
import { useSession } from "../../components/AuthProvider";
import { Panel } from "../../components/ui";
import SidebarLayout from "../../components/SidebarLayout";

export default function SettingsPage() {
  const router = useRouter();
  const { session, refreshSession: refresh } = useSession();
  const [teamName, setTeamName] = useState(session?.team?.name ?? "");
  const [saving, setSaving] = useState("");
  const [message, setMessage] = useState("");

  async function saveTeamName() {
    if (!teamName.trim()) return;
    setSaving("team");
    setMessage("");
    try {
      await postApi("/api/v1/settings/team", { name: teamName.trim() });
      setMessage("Team name updated.");
      await refresh();
    } catch { setMessage("Failed to update team name."); }
    setSaving("");
  }

  async function saveNotifications(pref: string) {
    setSaving(pref);
    setMessage("");
    try {
      await postApi("/api/v1/settings/notifications", { email_notifications: pref });
      setMessage(`Notification preference saved: ${pref}`);
    } catch { setMessage("Failed to save notification preference."); }
    setSaving("");
  }

  if (!session?.authenticated) { router.replace("/login"); return null; }

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900">Settings</h1>
          <p className="mt-1 text-sm text-slate-500">Manage your account and preferences</p>
        </header>

        {message && (
          <div className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm font-semibold text-emerald-800">
            {message}
          </div>
        )}

        <div className="grid gap-6">
          <Panel title="Profile">
            <div className="grid gap-3 text-sm">
              <div>
                <span className="text-xs font-semibold text-slate-400">Email</span>
                <p className="text-slate-700">{session.user?.email ?? "—"}</p>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400">Role</span>
                <p className="text-slate-700">{session.role ?? "viewer"}</p>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400">Team</span>
                <div className="mt-1 flex gap-2">
                  <input value={teamName} onChange={(e) => setTeamName(e.target.value)}
                    className="flex-1 rounded-md border border-slate-300 p-2 text-sm" />
                  <button disabled={saving === "team"} onClick={saveTeamName}
                    className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
                    {saving === "team" ? "Saving..." : "Save"}
                  </button>
                </div>
              </div>
            </div>
          </Panel>

          <Panel title="Email Notifications">
            <p className="mb-3 text-sm text-slate-500">Choose which notifications you&apos;d like to receive via email.</p>
            <div className="flex flex-wrap gap-2">
              {["all", "approvals", "none"].map((pref) => (
                <button key={pref} disabled={saving === pref} onClick={() => saveNotifications(pref)}
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50">
                  {saving === pref ? "Saving..." : pref.charAt(0).toUpperCase() + pref.slice(1)}
                </button>
              ))}
            </div>
          </Panel>

          <Panel title="API Keys">
            <p className="text-sm text-slate-500">Manage API keys for programmatic access. Coming soon.</p>
          </Panel>
        </div>
      </div>
    </SidebarLayout>
  );
}