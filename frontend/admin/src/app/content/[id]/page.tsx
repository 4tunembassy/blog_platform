import Link from "next/link";
import Badge from "@/components/Badge";
import ErrorBox from "@/components/ErrorBox";
import Loading from "@/components/Loading";
import TransitionPanel from "@/components/TransitionPanel";
import { getAllowed, getEvents } from "@/lib/api";
import { formatIso } from "@/lib/utils";

export default async function ContentDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const id = params.id;

  let allowed: Awaited<ReturnType<typeof getAllowed>> | null = null;
  let events: Awaited<ReturnType<typeof getEvents>> | null = null;
  let err: string | null = null;

  try {
    [allowed, events] = await Promise.all([getAllowed(id), getEvents(id)]);
  } catch (e: any) {
    err = e?.message || "Failed to load content detail";
  }

  if (err)
    return <ErrorBox title="Failed to load content detail" message={err} />;
  if (!allowed || !events) return <Loading />;

  return (
    <div className="py-2">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Content Detail</h1>
          <div className="mt-1 text-sm text-slate-700">
            <span className="font-medium">ID:</span>{" "}
            <code className="bg-slate-100 px-1 py-0.5 rounded">{id}</code>
          </div>
        </div>

        <Link
          href="/content"
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-100"
        >
          Back to list
        </Link>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-4 lg:col-span-1">
          <div className="font-medium">Current</div>

          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Badge tone="blue">from_state: {allowed.from_state}</Badge>
            <Badge
              tone={
                allowed.risk_tier <= 1
                  ? "green"
                  : allowed.risk_tier === 2
                  ? "amber"
                  : "red"
              }
            >
              Tier {allowed.risk_tier}
            </Badge>
          </div>

          <div className="mt-3 text-sm text-slate-700">
            <div className="font-medium">Allowed next states</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {allowed.allowed.map((s) => (
                <Badge key={s}>{s}</Badge>
              ))}
            </div>
          </div>
        </div>

        <div className="lg:col-span-2">
          <TransitionPanel contentId={id} allowed={allowed.allowed} />
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between">
          <div className="font-medium">Events</div>
          <div className="text-sm text-slate-600">{events.length} total</div>
        </div>

        <div className="mt-3 space-y-3">
          {events.map((ev) => (
            <div
              key={ev.id}
              className="rounded-lg border border-slate-200 bg-slate-50 p-3"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone="slate">{ev.event_type}</Badge>
                  <span className="text-sm text-slate-700">
                    actor: <span className="font-medium">{ev.actor_type}</span>
                    {ev.actor_id ? ` (${ev.actor_id})` : ""}
                  </span>
                </div>
                <div className="text-xs text-slate-600">
                  {formatIso(ev.created_at)}
                </div>
              </div>

              <pre className="mt-2 overflow-x-auto rounded-lg bg-white p-2 text-xs text-slate-800 border border-slate-200">
                {JSON.stringify(ev.payload, null, 2)}
              </pre>

              <div className="mt-2 text-xs text-slate-500">
                event_id: {ev.id}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
