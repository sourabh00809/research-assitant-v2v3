"use client";

import { useRouter } from "next/navigation";
import { useAuth, SignInButton } from "@clerk/nextjs";
import { LoadingSpinner } from "../../components/ui";

export default function LoginPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  if (isLoaded && isSignedIn) {
    router.replace("/projects");
    return null;
  }

  if (!isLoaded) return <LoadingSpinner text="Loading..." />;

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream">
      <div className="w-full max-w-md rounded-md border border-slate-300 bg-white p-8 text-center">
        <p className="text-xs font-bold uppercase tracking-wide text-emerald-700">AI Scientist</p>
        <h1 className="mt-2 text-2xl font-bold">Sign in to continue</h1>
        <p className="mt-1 text-sm text-slate-600">Click the button below to sign in with Clerk.</p>
        <SignInButton mode="modal">
          <button className="mt-6 inline-block rounded-md bg-emerald-700 px-6 py-3 text-sm font-bold text-white hover:bg-emerald-800">
            Sign In with Clerk
          </button>
        </SignInButton>
      </div>
    </div>
  );
}
