"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { postApi } from "../../lib/api";
import { useUser, useAuth } from "@clerk/nextjs";
import { Panel, LoadingSpinner } from "../../components/ui";
import SidebarLayout from "../../components/SidebarLayout";

const ADMIN_EMAIL = "sourabhnokhwal7@gmail.com";

function getRole(email: string | undefined): string {
  return email === ADMIN_EMAIL ? "admin" : "user";
}

export default function SettingsPage() {
  const router = useRouter();
  const { user } = useUser();
  const { isLoaded, isSignedIn } = useAuth();
  const [teamName, setTeamName] = useState("Research Lab");
  const [saving, setSaving] = useState("");
  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState<"success" | "error">("success");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  const [deleteConfirm, setDeleteConfirm] = useState("");
  const [deleting, setDeleting] = useState(false);

  function showMessage(msg: string, type: "success" | "error" = "success") {
    setMessage(msg);
    setMessageType(type);
  }

  async function saveTeamName() {
    if (!teamName.trim()) return;
    setSaving("team");
    setMessage("");
    try {
      await postApi("/api/v1/settings/team", { name: teamName.trim() });
      showMessage("Team name updated.");
    } catch { showMessage("Failed to update team name.", "error"); }
    setSaving("");
  }

  async function saveNotifications(pref: string) {
    setSaving(pref);
    setMessage("");
    try {
      await postApi("/api/v1/settings/notifications", { email_notifications: pref });
      showMessage(`Notification preference saved: ${pref}`);
    } catch { showMessage("Failed to save notification preference.", "error"); }
    setSaving("");
  }

  async function handlePasswordChange() {
    if (!currentPassword || !newPassword) {
      showMessage("Please fill in both fields.", "error");
      return;
    }
    if (newPassword.length < 8) {
      showMessage("New password must be at least 8 characters.", "error");
      return;
    }
    setChangingPassword(true);
    try {
      await user?.updatePassword({ currentPassword, newPassword });
      showMessage("Password changed successfully.");
      setCurrentPassword("");
      setNewPassword("");
    } catch (err: any) {
      showMessage(err?.errors?.[0]?.message || "Failed to change password.", "error");
    }
    setChangingPassword(false);
  }

  async function handleDeleteAccount() {
    if (deleteConfirm !== "DELETE") {
      showMessage('Type "DELETE" to confirm.', "error");
      return;
    }
    setDeleting(true);
    try {
      await user?.delete();
      router.replace("/");
    } catch (err: any) {
      showMessage(err?.errors?.[0]?.message || "Failed to delete account.", "error");
      setDeleting(false);
    }
  }

  if (!isLoaded) return <SidebarLayout><LoadingSpinner text="Loading..." /></SidebarLayout>;
  if (!isSignedIn) { router.replace("/login"); return null; }

  const role = getRole(user?.primaryEmailAddress?.emailAddress ?? undefined);

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-3xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900">Settings</h1>
          <p className="mt-1 text-sm text-slate-500">Manage your account and preferences</p>
        </header>

        {message && (
          <div className={`mb-4 rounded-md border p-3 text-sm font-semibold ${
            messageType === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border-red-200 bg-red-50 text-red-800"
          }`}>
            {message}
          </div>
        )}

        <div className="grid gap-6">
          <Panel title="Profile">
            <div className="grid gap-3 text-sm">
              <div>
                <span className="text-xs font-semibold text-slate-400">Email</span>
                <p className="text-slate-700">{user?.primaryEmailAddress?.emailAddress ?? "—"}</p>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400">Role</span>
                <p className="text-slate-700">{role}</p>
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

          <Panel title="Change Password">
            <p className="mb-3 text-sm text-slate-500">Update your account password.</p>
            <div className="grid gap-3">
              <input type="password" placeholder="Current password" value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="rounded-md border border-slate-300 p-2 text-sm" />
              <input type="password" placeholder="New password (min 8 chars)" value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="rounded-md border border-slate-300 p-2 text-sm" />
              <button disabled={changingPassword} onClick={handlePasswordChange}
                className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
                {changingPassword ? "Changing..." : "Change Password"}
              </button>
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

          <Panel title="Delete Account">
            <p className="mb-3 text-sm text-red-600">This action is permanent and cannot be undone.</p>
            <div className="grid gap-3">
              <input type="text" placeholder='Type "DELETE" to confirm' value={deleteConfirm}
                onChange={(e) => setDeleteConfirm(e.target.value)}
                className="rounded-md border border-red-300 p-2 text-sm" />
              <button disabled={deleting || deleteConfirm !== "DELETE"} onClick={handleDeleteAccount}
                className="rounded-md bg-red-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">
                {deleting ? "Deleting..." : "Delete Account"}
              </button>
            </div>
          </Panel>
        </div>
      </div>
    </SidebarLayout>
  );
}