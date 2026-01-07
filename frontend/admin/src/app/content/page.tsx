import Link from "next/link";
import Badge from "@/components/Badge";
import ErrorBox from "@/components/ErrorBox";
import Loading from "@/components/Loading";
import Pagination from "@/components/Pagination";
import Table from "@/components/Table";
import { listContent } from "@/lib/api";
import { formatIso } from "@/lib/utils";

export default async function ContentListPage({
  searchParams,
}: {
  searchParams: {
    limit?: string;
    offset?: string;
    sort?: string;
    q?: string;
  };
}) {
  const limit = Number(searchParams.limit ?? "20");
  const offset = Number(searchParams.offset ?? "0");
  const sort = searchParams.sort ?? "created_at_desc";
  const q = searchParams.q ?? "";

  let data: Awaited<ReturnType<typeof listContent>> | null = null;
  let err: string | null = null;

  try {
    data = await listContent({
      limit: Number.isFinite(limit) ? limit : 20,
      offset: Number.isFinite(offset) ? offset : 0,
      sort,
      q: q || undefined,
    });
  } catch (e: any) {
    err = e?.message || "Failed to load content list";
  }

  if (err) return <ErrorBox title="Failed to load /content" message={err} />;
  if (!data) return <Loading />;

  const baseQuery = (next: {
    limit?: number;
    offset?: number;
    sort?: string;
    q?: string;
  }) => {
    const sp = new URLSearchParams();
    sp.set("limit", String(next.limit ?? data!.limit));
    sp.set("offset", String(next.offset ?? data!.offset));
    sp.set("sort", String(next.sort ?? sort));
    if (typeof next.q === "string" ? next.q.length > 0 : q.length > 0) {
      sp.set("q", typeof next.q === "string" ? next.q : q);
    }
    return `/content?${sp.toString()}`;
  };

  return (
    <div className="py-2">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Content</h1>
          <p className="mt-1 text-sm text-slate-700">
            List + search + open detail view (events, allowed transitions,
            transition action).
          </p>
        </div>

        <form
          className="flex items-center gap-2"
          action="/content"
          method="get"
        >
          <input type="hidden" name="limit" value={String(data.limit)} />
          <input type="hidden" name="offset" value={"0"} />
          <input type="hidden" name="sort" value={sort} />
          <input
            className="w-64 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
            placeholder="Search title (q=...)"
            name="q"
            defaultValue={q}
          />
          <button className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800">
            Search
          </button>
          <Link
            className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-100"
            href={baseQuery({ q: "" })}
          >
            Clear
          </Link>
        </form>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-slate-700">Sort:</span>
          <Link
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 hover:bg-slate-100"
            href={baseQuery({ sort: "created_at_desc", offset: 0 })}
          >
            created_at_desc
          </Link>
          <Link
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 hover:bg-slate-100"
            href={baseQuery({ sort: "created_at_asc", offset: 0 })}
          >
            created_at_asc
          </Link>
        </div>

        <Pagination
          limit={data.limit}
          offset={data.offset}
          total={data.total}
          onChange={(nextOffset) => {
            // server component: use link navigation
          }}
        />
      </div>

      {/* Pagination links (server-friendly) */}
      <div className="mt-2 flex justify-end gap-2">
        <Link
          className={`rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-100 ${
            data.offset <= 0 ? "pointer-events-none opacity-50" : ""
          }`}
          href={baseQuery({ offset: Math.max(0, data.offset - data.limit) })}
        >
          Prev
        </Link>
        <Link
          className={`rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-100 ${
            data.offset + data.limit >= data.total
              ? "pointer-events-none opacity-50"
              : ""
          }`}
          href={baseQuery({ offset: data.offset + data.limit })}
        >
          Next
        </Link>
      </div>

      <div className="mt-4">
        <Table>
          <thead className="bg-slate-100 text-left">
            <tr>
              <th className="px-4 py-3">Title</th>
              <th className="px-4 py-3">State</th>
              <th className="px-4 py-3">Risk Tier</th>
              <th className="px-4 py-3">Created</th>
              <th className="px-4 py-3">Updated</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((it) => (
              <tr key={it.id} className="border-t border-slate-200">
                <td className="px-4 py-3">
                  <Link
                    className="font-medium hover:underline"
                    href={`/content/${it.id}`}
                  >
                    {it.title}
                  </Link>
                  <div className="mt-1 text-xs text-slate-500">{it.id}</div>
                </td>
                <td className="px-4 py-3">
                  <Badge tone={it.state === "PUBLISHED" ? "green" : "slate"}>
                    {it.state}
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  <Badge
                    tone={
                      it.risk_tier <= 1
                        ? "green"
                        : it.risk_tier === 2
                        ? "amber"
                        : "red"
                    }
                  >
                    Tier {it.risk_tier}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {formatIso(it.created_at)}
                </td>
                <td className="px-4 py-3 text-slate-700">
                  {formatIso(it.updated_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </Table>
      </div>
    </div>
  );
}
