"use client";

import { useState } from "react";

export default function NewContentPage() {
  const [title, setTitle] = useState("Office Step3 Test");
  const [riskTier, setRiskTier] = useState(1);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState<string>("");

  async function submit() {
    setErr("");
    setResult(null);

    try {
      const res = await fetch("http://127.0.0.1:8000/content", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Tenant-Slug": "default",
        },
        body: JSON.stringify({ title, risk_tier: Number(riskTier) }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(JSON.stringify(data));
      setResult(data);
    } catch (e: any) {
      setErr(e?.message || "Request failed");
    }
  }

  return (
    <main style={{ padding: 24, fontFamily: "system-ui, sans-serif", maxWidth: 720 }}>
      <h1>Create Content</h1>

      <label style={{ display: "block", marginTop: 12 }}>
        Title
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ width: "100%", padding: 10, marginTop: 6 }}
        />
      </label>

      <label style={{ display: "block", marginTop: 12 }}>
        Risk tier (1-3)
        <input
          type="number"
          min={1}
          max={3}
          value={riskTier}
          onChange={(e) => setRiskTier(Number(e.target.value))}
          style={{ width: "100%", padding: 10, marginTop: 6 }}
        />
      </label>

      <button onClick={submit} style={{ marginTop: 16, padding: "10px 14px", cursor: "pointer" }}>
        Create
      </button>

      {err ? (
        <pre style={{ marginTop: 16, whiteSpace: "pre-wrap", color: "crimson" }}>{err}</pre>
      ) : null}

      {result ? (
        <section style={{ marginTop: 16 }}>
          <h2>Created</h2>
          <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(result, null, 2)}</pre>
          <p>
            View: <a href={`/content/${result.id}`}>{result.id}</a>
          </p>
        </section>
      ) : null}
    </main>
  );
}
