"use client";

import type { EvidenceItem } from "../lib/api";
import { StatusBadge } from "./ui";

export default function EvidenceCard({ item }: { item: EvidenceItem }) {
  return (
    <article className="rounded-md border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusBadge value={item.extraction_type} />
        <span className="max-w-[12rem] truncate text-xs text-slate-500" title={item.source_id}>
          {item.source_id}
        </span>
      </div>
      <p className="mt-3 line-clamp-4 text-sm leading-6 text-slate-800">{item.claim}</p>
    </article>
  );
}
