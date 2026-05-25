"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { postApi } from "../../lib/api";
import { useSession } from "../../components/AuthProvider";
import { ErrorBanner } from "../../components/ui";

export default function LoginPage() {
  const router = useRouter();
  const { session, refreshSession } = useSession();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"signup" | "login">("signup");

  if (session?.authenticated) {
    router.replace("/dashboard");
    return null;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") ?? "");
    const password = String(form.get("password") ?? "");
    const team_name = String(form.get("team_name") ?? "");
    const confirm_password = String(form.get("confirm_password") ?? "");

    if (mode === "signup") {
      if (password.length < 8) {
        setError("Password must be at least 8 characters.");
        setBusy(false);
        return;
      }
      if (password !== confirm_password) {
        setError("Passwords do not match.");
        setBusy(false);
        return;
      }
      try {
        await postApi("/api/v1/auth/signup", { email, password, team_name });
        await refreshSession();
        router.push("/dashboard");
        return;
      } catch (err) {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("409")) {
          setMode("login");
          try {
            await postApi("/api/v1/auth/login", { email, password });
            await refreshSession();
            router.push("/dashboard");
            return;
          } catch {
            setError("Email already registered. Try signing in.");
            setBusy(false);
            return;
          }
        }
        setError(msg || "Sign up failed. Check your information.");
        setBusy(false);
        return;
      }
    }

    try {
      await postApi("/api/v1/auth/login", { email, password });
      await refreshSession();
      router.push("/dashboard");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      if (msg.includes("429")) {
        setError("Too many attempts. Try again later.");
      } else {
        setError("Sign in failed. Check your email and password.");
      }
    }
    setBusy(false);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream">
      <div className="w-full max-w-md rounded-md border border-slate-300 bg-white p-8">
        <div className="mb-6 text-center">
          <p className="text-xs font-bold uppercase tracking-wide text-emerald-700">AI Scientist</p>
          <h1 className="mt-2 text-2xl font-bold">{mode === "signup" ? "Create Account" : "Sign In"}</h1>
          <p className="mt-1 text-sm text-slate-600">
            {mode === "signup" ? "Start your research workspace" : "Welcome back"}
          </p>
        </div>
        {error && <ErrorBanner message={error} />}
        <form className="mt-4 grid gap-4" onSubmit={handleSubmit}>
          <input
            className="rounded-md border border-slate-300 p-2 text-sm"
            name="email"
            type="email"
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
          <input
            className="rounded-md border border-slate-300 p-2 text-sm"
            name="password"
            type="password"
            placeholder={mode === "signup" ? "Create a password (min 8 chars)" : "Password"}
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            minLength={8}
            required
          />
          {mode === "signup" && (
            <>
              <input
                className="rounded-md border border-slate-300 p-2 text-sm"
                name="confirm_password"
                type="password"
                placeholder="Confirm password"
                autoComplete="new-password"
                minLength={8}
                required
              />
              <input
                className="rounded-md border border-slate-300 p-2 text-sm"
                name="team_name"
                placeholder="Team name (optional)"
              />
            </>
          )}
          <button
            className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
            disabled={busy}
          >
            {busy ? "Please wait..." : mode === "signup" ? "Create Account" : "Sign In"}
          </button>
        </form>
        <p className="mt-4 text-center text-xs text-slate-500">
          {mode === "signup" ? (
            <>Already have an account?{" "}<button className="font-semibold text-emerald-700 hover:underline" onClick={() => { setMode("login"); setError(""); }}>Sign In</button></>
          ) : (
            <>New here?{" "}<button className="font-semibold text-emerald-700 hover:underline" onClick={() => { setMode("signup"); setError(""); }}>Create Account</button></>
          )}
        </p>
      </div>
    </div>
  );
}
