"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "@clerk/nextjs";

function Svg({ children, className = "h-4 w-4" }: { children: React.ReactNode; className?: string }) {
  return <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}>{children}</svg>;
}

const ICONS: Record<string, React.ReactNode> = {
  projects: <Svg><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" /></Svg>,
  agents: <Svg><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" /><circle cx="12" cy="7" r="4" /></Svg>,
  billing: <Svg><text x="12" y="16" textAnchor="middle" fontSize="14" fontWeight="bold" stroke="none" fill="currentColor">₹</text><circle cx="12" cy="12" r="10" /></Svg>,
  settings: <Svg><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 01-2.83 2.83l-.06-.06a1.65 1.65 0 00-2.09-.33A1.65 1.65 0 0013.5 19.86V21a2 2 0 01-4 0v-.09a1.65 1.65 0 00-1.41-1.41 1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.77-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z" /></Svg>,
  workspace: <Svg><rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></Svg>,
  evidence: <Svg><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2" /><rect x="8" y="2" width="8" height="4" rx="1" /><path d="M9 14l2 2 4-4" /></Svg>,
  experiments: <Svg><path d="M4 22h16" /><path d="M6 18V2h2v16" /><path d="M14 18V2h2v16" /><path d="M10 10h4" /><path d="M12 18v4" /></Svg>,
  graph: <Svg><path d="M18 20V10" /><path d="M12 20V4" /><path d="M6 20v-6" /></Svg>,
  memory: <Svg><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></Svg>,
  "source-library": <Svg><path d="M4 19.5A2.5 2.5 0 016.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z" /><line x1="8" y1="7" x2="16" y2="7" /><line x1="8" y1="11" x2="14" y2="11" /></Svg>,
};

const GLOBAL_LINKS = [
  { href: "/projects", label: "Projects", icon: "projects" },
  { href: "/agents", label: "Agents", icon: "agents" },
  { href: "/billing", label: "Billing", icon: "billing" },
  { href: "/settings", label: "Settings", icon: "settings" },
] as const;

const PROJECT_LINKS = [
  { href: "workspace", label: "Workspace", icon: "workspace" },
  { href: "evidence", label: "Evidence", icon: "evidence" },
  { href: "experiments", label: "Experiments", icon: "experiments" },
  { href: "graph", label: "Research Graph", icon: "graph" },
  { href: "memory", label: "Memory", icon: "memory" },
  { href: "papers", label: "Source Library", icon: "source-library" },
] as const;

function isActive(pathname: string, href: string): boolean {
  if (href === "/projects") return pathname === "/projects";
  return pathname.startsWith(href);
}

export default function Sidebar() {
  const pathname = usePathname();
  const { user, isSignedIn } = useUser();
  const projectMatch = pathname.match(/^\/projects\/([^/]+)/);
  const projectId = projectMatch?.[1];

  if (!isSignedIn) return null;

  return (
    <aside className="flex w-60 flex-col border-r border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-4 py-4">
        <Link href="/projects" className="text-xs font-bold uppercase tracking-wide text-emerald-700 hover:text-emerald-600">
          Research Assistant
        </Link>
        <p className="mt-1 truncate text-xs text-slate-500">{user?.primaryEmailAddress?.emailAddress ?? "Researcher"}</p>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {GLOBAL_LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
              isActive(pathname, link.href)
                ? "bg-emerald-100 text-emerald-900"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {ICONS[link.icon]}
            {link.label}
          </Link>
        ))}

        {projectId && (
          <>
            <hr className="my-3 border-slate-200" />
            <p className="mb-2 px-3 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Project
            </p>
            {PROJECT_LINKS.map((link) => (
              <Link
                key={link.href}
                href={`/projects/${projectId}/${link.href}`}
                className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  pathname === `/projects/${projectId}/${link.href}` || pathname.startsWith(`/projects/${projectId}/${link.href}/`)
                    ? "bg-emerald-100 text-emerald-900"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {ICONS[link.icon]}
                {link.label}
              </Link>
            ))}
          </>
        )}
      </nav>

      <div className="border-t border-slate-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
            {user?.primaryEmailAddress?.emailAddress === "sourabhnokhwal7@gmail.com" ? "admin" : "user"}
          </span>
          <Link href="/projects" className="text-xs text-emerald-600 hover:text-emerald-700">
            Projects
          </Link>
        </div>
      </div>
    </aside>
  );
}
