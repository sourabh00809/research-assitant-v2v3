"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { postApi } from "../../lib/api";
import { useUser, useAuth } from "@clerk/nextjs";
import { Panel, LoadingSpinner } from "../../components/ui";
import SidebarLayout from "../../components/SidebarLayout";

const ADMIN_EMAIL = process.env.NEXT_PUBLIC_ADMIN_EMAIL || "";

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
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100">Settings</h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Manage your account and preferences</p>
        </header>

        {message && (
          <div className={`mb-4 rounded-md border p-3 text-sm font-semibold ${
            messageType === "success"
              ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300"
              : "border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-900/30 dark:text-red-300"
          }`}>
            {message}
          </div>
        )}

        <div className="grid gap-6">
          <Panel title="Profile">
            <div className="grid gap-3 text-sm">
              <div>
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">Email</span>
                <p className="text-slate-700 dark:text-slate-200">{user?.primaryEmailAddress?.emailAddress ?? "—"}</p>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">Role</span>
                <p className="text-slate-700 dark:text-slate-200">{role}</p>
              </div>
              <div>
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">Team</span>
                <div className="mt-1 flex gap-2">
                  <input value={teamName} onChange={(e) => setTeamName(e.target.value)}
                    className="flex-1 rounded-md border border-slate-300 p-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" />
                  <button disabled={saving === "team"} onClick={saveTeamName}
                    className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50 dark:bg-emerald-600 dark:hover:bg-emerald-500">
                    {saving === "team" ? "Saving..." : "Save"}
                  </button>
                </div>
              </div>
            </div>
          </Panel>

          <Panel title="Change Password">
            <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">Update your account password.</p>
            <div className="grid gap-3">
              <input type="password" placeholder="Current password" value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="rounded-md border border-slate-300 p-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" />
              <input type="password" placeholder="New password (min 8 chars)" value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="rounded-md border border-slate-300 p-2 text-sm dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100" />
              <button disabled={changingPassword} onClick={handlePasswordChange}
                className="rounded-md bg-emerald-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50 dark:bg-emerald-600 dark:hover:bg-emerald-500">
                {changingPassword ? "Changing..." : "Change Password"}
              </button>
            </div>
          </Panel>

          <Panel title="Email Notifications">
            <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">Choose which notifications you&apos;d like to receive via email.</p>
            <div className="flex flex-wrap gap-2">
              {["all", "approvals", "none"].map((pref) => (
                <button key={pref} disabled={saving === pref} onClick={() => saveNotifications(pref)}
                  className="rounded-md border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-600 hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700/50">
                  {saving === pref ? "Saving..." : pref.charAt(0).toUpperCase() + pref.slice(1)}
                </button>
              ))}
            </div>
          </Panel>

          <Panel title="API Keys">
            <p className="text-sm text-slate-500 dark:text-slate-400">Manage API keys for programmatic access. Coming soon.</p>
          </Panel>

          <Panel title="Delete Account">
            <p className="mb-3 text-sm text-red-600 dark:text-red-400">This action is permanent and cannot be undone.</p>
            <div className="grid gap-3">
              <input type="text" placeholder='Type "DELETE" to confirm' value={deleteConfirm}
                onChange={(e) => setDeleteConfirm(e.target.value)}
                className="rounded-md border border-red-300 p-2 text-sm dark:border-red-800 dark:bg-slate-800 dark:text-slate-100" />
              <button disabled={deleting || deleteConfirm !== "DELETE"} onClick={handleDeleteAccount}
                className="rounded-md bg-red-700 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50 dark:bg-red-600">
                {deleting ? "Deleting..." : "Delete Account"}
              </button>
            </div>
          </Panel>
        </div>
      </div>
    </SidebarLayout>
  );
}