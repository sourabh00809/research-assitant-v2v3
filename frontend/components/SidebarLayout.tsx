"use client";

import { useSession } from "./AuthProvider";
import Sidebar from "./Sidebar";

export default function SidebarLayout({ children }: { children: React.ReactNode }) {
  const { session } = useSession();
  return (
    <div className="flex min-h-screen bg-[#f6f4ef]">
      <Sidebar session={session} />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
