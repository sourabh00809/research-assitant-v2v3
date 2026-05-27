"use client";

import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import type { Project } from "../../../../lib/api";
import { useAuth } from "@clerk/nextjs";
import { api } from "../../../../lib/api";
import { Panel, EmptyState, StatusBadge, LoadingSpinner } from "../../../../components/ui";
import SidebarLayout from "../../../../components/SidebarLayout";

export default function MemoryPage() {
  const params = useParams();
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const projectId = params.id as string;
  const { data: projects, error, isLoading } = useSWR<Project[]>("/api/v1/projects", api);
  const project = projects?.find((p) => p.id === projectId);
  const memory = project?.memory ?? [];

  if (!isLoaded) return <SidebarLayout><LoadingSpinner text="Loading research memory..." /></SidebarLayout>;
  if (!isSignedIn) { router.replace("/login"); return null; }

  if (isLoading) return <SidebarLayout><LoadingSpinner text="Loading research memory..." /></SidebarLayout>;

  if (error) return <SidebarLayout><div className="mx-auto max-w-5xl px-4 py-6"><div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">Failed to load memory.</div></div></SidebarLayout>;

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900">Research Memory</h1>
          <p className="mt-1 text-sm text-slate-500">{project?.name} · {memory.length} saved items</p>
        </header>

        {memory.length ? (
          <div className="grid gap-3">
            {memory.map((item: any) => (
              <article key={item.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <StatusBadge value={item.kind ?? "note"} />
                  {item.tags?.map((tag: string) => (
                    <span key={tag} className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">{tag}</span>
                  ))}
                </div>
                <p className="text-sm text-slate-800">{item.content}</p>
                {item.source_ids?.length > 0 && (
                  <p className="mt-2 text-xs text-slate-400">Sources: {item.source_ids.join(", ")}</p>
                )}
              </article>
            ))}
          </div>
        ) : (
          <EmptyState text="Run investigations to automatically build research memory, or use annotations to save findings." />
        )}
      </div>
    </SidebarLayout>
  );
}