import Link from "next/link";

export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-white dark:bg-slate-900">
      <div className="text-center">
        <h1 className="mb-2 text-6xl font-bold text-slate-300 dark:text-slate-600">404</h1>
        <p className="mb-6 text-slate-500 dark:text-slate-400">Page not found</p>
        <Link
          href="/projects"
          className="rounded bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800"
        >
          Go to Projects
        </Link>
      </div>
    </div>
  );
}
