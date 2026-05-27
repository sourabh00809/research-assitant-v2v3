"use client";

import { useEffect, type ReactNode } from "react";
import { ClerkProvider, useAuth } from "@clerk/nextjs";
import { setTokenProvider } from "../lib/api";

function TokenSetter({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  useEffect(() => {
    setTokenProvider(() => getToken({ template: "supabase" }));
  }, [getToken]);
  return <>{children}</>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <ClerkProvider publishableKey={process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY}>
      <TokenSetter>{children}</TokenSetter>
    </ClerkProvider>
  );
}
