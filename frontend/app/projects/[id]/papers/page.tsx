"use client";

import { useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import useSWR from "swr";
import type { Project } from "../../../../lib/api";
import { api } from "../../../../lib/api";
import { useAuth } from "@clerk/nextjs";
import { Panel, EmptyState, StatusBadge, LoadingSpinner } from "../../../../components/ui";
import SidebarLayout from "../../../../components/SidebarLayout";

export default function PapersPage() {
  const params = useParams();
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const projectId = params.id as string;
  const { data: projects, mutate, isLoading } = useSWR<Project[]>("/api/v1/projects", api);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [useUnstructured, setUseUnstructured] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const project = projects?.find((p) => p.id === projectId);
  const papers = project?.uploaded_papers ?? [];

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError("");
    try {
      const fd = new FormData();
      fd.append("file", file);
      let url = `/api/projects/${projectId}/papers/upload?filename=${encodeURIComponent(file.name)}`;
      if (useUnstructured) url += "&parser=unstructured";
      const res = await fetch(url, {
        method: "POST",
        credentials: "include",
        body: fd,
      });
      if (!res.ok) throw new Error(await res.text());
      await mutate();
      if (fileRef.current) fileRef.current.value = "";
    } catch (err: any) {
      setUploadError(err.message || "Upload failed");
    }
    setUploading(false);
  }

  if (!isLoaded) return <SidebarLayout><LoadingSpinner text="Loading..." /></SidebarLayout>;
  if (!isSignedIn) { router.replace("/sign-in"); return null; }

  if (isLoading) return <SidebarLayout><LoadingSpinner text="Loading papers..." /></SidebarLayout>;

  return (
    <SidebarLayout>
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6">
          <h1 className="text-3xl font-bold text-slate-900">Source Library</h1>
          <p className="mt-1 text-sm text-slate-500">{project?.name} · {papers.length} papers</p>
        </header>

        <div className="mb-6">
          <Panel title="Upload Paper">
            <p className="mb-3 text-sm text-slate-500">Upload a PDF to extract text and add to the project source library.</p>
            <div className="flex flex-wrap gap-3">
              <input ref={fileRef} type="file" accept=".pdf" className="rounded-md border border-slate-300 p-2 text-sm" />
              <button disabled={uploading} onClick={handleUpload}
                className="rounded-md bg-emerald-700 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-800 disabled:opacity-50">
                {uploading ? "Uploading..." : "Upload"}
              </button>
            </div>
            <label className="mt-3 flex items-center gap-1.5 text-sm text-slate-600">
              <input
                type="checkbox"
                checked={useUnstructured}
                onChange={(e) => setUseUnstructured(e.target.checked)}
                className="rounded border-slate-300 text-emerald-700 focus:ring-emerald-500"
              />
              Use Unstructured API for enhanced PDF parsing (requires UNSTRUCTURED_API_KEY)
            </label>
            {uploadError && <p className="mt-2 text-sm text-red-600">{uploadError}</p>}
          </Panel>
        </div>

        {papers.length ? (
          <div className="grid gap-3">
            {papers.map((paper: any) => (
              <article key={paper.id} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h3 className="font-semibold text-slate-900">{paper.title || paper.filename || "Untitled"}</h3>
                    <p className="mt-1 text-xs text-slate-400">
                      {paper.source_type ?? "pdf"} · {paper.page_count ? `${paper.page_count} pages` : ""} · {paper.filename ?? ""}
                    </p>
                  </div>
                  <StatusBadge value={paper.ingestion_status || "pending"} />
                </div>
              </article>
            ))}
          </div>
        ) : (
          <EmptyState text="Upload PDFs or run investigations to populate the source library with relevant papers." />
        )}
      </div>
    </SidebarLayout>
  );
}