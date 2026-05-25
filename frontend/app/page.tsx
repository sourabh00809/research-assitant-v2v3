"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "../components/AuthProvider";
import { LoadingSpinner } from "../components/ui";

export default function Home() {
  const router = useRouter();
  const { session } = useSession();

  useEffect(() => {
    if (session?.authenticated) {
      router.replace("/projects");
    } else {
      router.replace("/login");
    }
  }, [session, router]);

  return <LoadingSpinner text="Redirecting..." />;
}