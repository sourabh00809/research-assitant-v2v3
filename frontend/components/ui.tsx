"use client";

export function StatusBadge({ value }: { value: string }) {
  return <span className="rounded-full bg-emerald-100 px-2 py-1 text-xs font-bold uppercase text-emerald-800">{value || "unknown"}</span>;
}

export function MetricCard({ title, value, detail }: { title: string; value: number | string; detail: string }) {
  return (
    <div className="rounded-md border border-slate-300 bg-white p-4">
      <p className="text-sm font-semibold text-slate-600">{title}</p>
      <strong className="mt-1 block truncate text-2xl">{value}</strong>
      <p className="mt-1 text-xs text-slate-500">{detail}</p>
    </div>
  );
}

export function EmptyState({ text }: { text: string }) {
  return <p className="rounded-md border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">{text}</p>;
}

export function Panel({ children, title, meta, className = "" }: { children: React.ReactNode; title: string; meta?: string; className?: string }) {
  return (
    <section className={`rounded-md border border-slate-300 bg-white p-5 ${className}`}>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-bold">{title}</h2>
        {meta && <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">{meta}</span>}
      </div>
      {children}
    </section>
  );
}

export function LoadingSpinner({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-slate-300 border-t-emerald-700" />
      <p className="ml-3 text-sm text-slate-500">{text}</p>
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-4">
      <p className="text-sm font-semibold text-red-800">{message}</p>
    </div>
  );
}

export function labelize(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}
