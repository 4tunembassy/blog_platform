"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";

type Content = {
  id: string;
  title: string;
  state: string;
  risk_tier: number;
  created_at: string;
  updated_at: string;
};

export default function ContentDetailPage() {
  const params = useParams<{ id: string }>();
  const id = useMemo(() => (params?.id as string) || "", [params]);

  const [content, setContent] = useState<Content | null>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [allowed, setAllowed] = useState<string[]>([]);
  const [toState, setToState] = useState<string>("");
  const [err, setErr] = useState<string>("");

  async function load() {
    setErr("");
    try {
      const [cRes, eRes, aRes] = await Promise.all([
        fetch(`http://127.0.0.1:8000/content/${id}`, { headers: { "X-Tenant-Slug": "default" } }),
        fetch(`http://127.0.0.1:8000/content/${id}/events`, { headers: { "X-Tenant-Slug": "default" } }),
        fetch(`http://127.0.0.1:8000/content/${id}/allowed`, { headers: { "X-Tenant-Slug": "default" } }),
      ]);

      const c = await cRes.json();
      const e = await eRes.json();
      const a = await aRes.json();

      if (!cRes.ok) throw new Error(JSON.stringify(c));
      if (!eRes.ok) throw new Error(JSON.stringify(e));
      if (!aRes.ok) throw new Error(JSON.stringify(a));

      setContent(c);
      setEvents(Array.isArray(e) ? e : []);
      setAllowed(Array.isArray(a.allowed) ? a.allowed : []);
      setToState((Array.isArray(a.allowed) && a.allowed[0]) ? a.allowed[0] : "");
    } catch (ex: any) {
      setErr(ex?.message || "Load failed");
    }
  }

  useEffect(() => {
    if (id) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function transition() {
    if (!toState) return;
    setErr("");
    try {
      const res = await fetch(`http://127.0.0.1:8000/content/${id}/transition`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-Slug": "default",
        },
        body: JSON.stringify({ to_state: toState, reason: "UI transition", actor_type: "system" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      await load();
    } catch (ex: any) {
      setErr(ex?.message || "Transition failed");
    }
  }

  return (
    <main style={{ padding: 24, fontFamily: "system-ui, sans-serif", maxWidth: 900 }}>
      <h1>Content</h1>

      {err ? <pre style={{ whiteSpace: "pre-wrap", color: "crimson" }}>{err}</pre> : null}

      {content ? (
        <section>
          <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(content, null, 2)}</pre>

          <div style={{ marginTop: 12, display: "flex", gap: 8, alignItems: "center" }}>
            <select value={toState} onChange={(e) => setToState(e.target.value)} style={{ padding: 8 }}>
              {allowed.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
            <button onClick={transition} style={{ padding: "8px 12px", cursor: "pointer" }}>
              Transition
            </button>
            <button onClick={load} style={{ padding: "8px 12px", cursor: "pointer" }}>
              Refresh
            </button>
          </div>

          <h2 style={{ marginTop: 20 }}>Events</h2>
          <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(events, null, 2)}</pre>
        </section>
      ) : (
        <p>Loading...</p>
      )}
    </main>
  );
}
