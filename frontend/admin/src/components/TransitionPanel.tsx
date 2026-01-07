"use client";

import { useMemo, useState } from "react";
import ErrorBox from "@/components/ErrorBox";
import { transitionContent } from "@/lib/api";

export default function TransitionPanel({
  contentId,
  allowed,
}: {
  contentId: string;
  allowed: string[];
}) {
  const options = useMemo(() => allowed ?? [], [allowed]);
  const [toState, setToState] = useState(options[0] ?? "");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [okMsg, setOkMsg] = useState<string | null>(null);

  async function doTransition() {
    setErr(null);
    setOkMsg(null);

    if (!toState) return;

    setBusy(true);
    try {
      const res = await transitionContent(contentId, { to_state: toState });
      setOkMsg(`Transitioned: ${res.from_state} → ${res.to_state}`);
    } catch (e: any) {
      setErr(e?.message || "Transition failed");
    } finally {
      setBusy(false);
    }
  }

  if (!options.length) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-700">
        No allowed transitions available.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="font-medium">Transition</div>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        <select
          className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
          value={toState}
          onChange={(e) => setToState(e.target.value)}
          disabled={busy}
        >
          {options.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <button
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm text-white hover:bg-slate-800 disabled:opacity-50"
          onClick={doTransition}
          disabled={busy || !toState}
        >
          {busy ? "Transitioning..." : "Apply"}
        </button>

        <button
          className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm hover:bg-slate-100 disabled:opacity-50"
          onClick={() => window.location.reload()}
          disabled={busy}
        >
          Refresh page
        </button>
      </div>

      {okMsg && (
        <div className="mt-3 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          {okMsg} (refresh to see updated allowed + events)
        </div>
      )}

      {err && (
        <div className="mt-3">
          <ErrorBox message={err} />
        </div>
      )}
    </div>
  );
}
