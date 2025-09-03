"use client";

import { useState } from "react";

export function ReplayButton({ runId }: { runId: string }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<any | null>(null);

  const onClick = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(
        `http://localhost:8000/api/runs/${runId}/replay`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ max_steps: 5 }),
        }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setResult(data.result);
    } catch (e: any) {
      setError(e?.message || "Replay failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <button
        onClick={onClick}
        disabled={loading}
        className="inline-flex items-center rounded bg-black px-3 py-1.5 text-white text-sm disabled:opacity-50"
      >
        {loading ? "Replaying..." : "Replay deterministically"}
      </button>
      {error && <div className="text-sm text-red-600">{error}</div>}
      {result && (
        <div className="rounded border p-3">
          <div className="text-sm font-medium mb-1">Replay result</div>
          <pre className="text-xs whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
