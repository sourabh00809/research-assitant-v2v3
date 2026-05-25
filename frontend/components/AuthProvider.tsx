"use client";

import { createContext, useContext, useMemo } from "react";
import useSWR from "swr";
import type { Session } from "../lib/api";
import { api } from "../lib/api";
import { LoadingSpinner } from "./ui";

const SessionContext = createContext<{ session?: Session; refreshSession: () => void }>({
  refreshSession: () => {},
});

export function useSession() {
  return useContext(SessionContext);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { data: session, error, mutate, isLoading } = useSWR<Session>("/api/v1/auth/session", api);

  const value = useMemo(() => ({ session, refreshSession: mutate }), [session, mutate]);

  if (error) return (
    <div className="flex min-h-screen items-center justify-center bg-[#f6f4ef]">
      <div className="rounded-md border border-red-200 bg-red-50 p-6 text-center">
        <p className="text-sm font-semibold text-red-800">Failed to load session</p>
        <button onClick={() => mutate()} className="mt-3 rounded-md bg-red-700 px-4 py-2 text-sm font-semibold text-white hover:bg-red-800">
          Retry
        </button>
      </div>
    </div>
  );

  if (isLoading) return <LoadingSpinner text="Loading workspace..." />;

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
