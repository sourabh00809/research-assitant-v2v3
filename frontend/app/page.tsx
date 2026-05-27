"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { LoadingSpinner } from "../components/ui";

export default function Home() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();

  useEffect(() => {
    if (!isLoaded) return;
    if (isSignedIn) {
      router.replace("/projects");
    } else {
      router.replace("/login");
    }
  }, [isLoaded, isSignedIn, router]);

  return <LoadingSpinner text="Redirecting..." />;
}