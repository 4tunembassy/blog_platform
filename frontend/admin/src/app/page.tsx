import Link from "next/link";

export default function HomePage() {
  return (
    <div className="py-6">
      <h1 className="text-2xl font-semibold">Admin Console</h1>
      <p className="mt-2 text-slate-700">
        Governance-first UI for Content lifecycle, transitions, and provenance
        events.
      </p>

      <div className="mt-6 flex gap-3">
        <Link
          href="/content"
          className="rounded-lg bg-slate-900 px-4 py-2 text-white hover:bg-slate-800"
        >
          Open Content
        </Link>
        <a
          href="/content?limit=20&offset=0&sort=created_at_desc"
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 hover:bg-slate-100"
        >
          Content (default query)
        </a>
      </div>

      <div className="mt-8 rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="font-medium">Environment</h2>
        <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
          <li>
            API Base URL:{" "}
            <code className="bg-slate-100 px-1 py-0.5 rounded">
              NEXT_PUBLIC_API_BASE_URL
            </code>
          </li>
          <li>
            Tenant slug header:{" "}
            <code className="bg-slate-100 px-1 py-0.5 rounded">
              X-Tenant-Slug
            </code>
          </li>
        </ul>
      </div>
    </div>
  );
}
