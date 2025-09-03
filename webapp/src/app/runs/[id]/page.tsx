import { ReplayButton } from "@/components/replay-button";
import { JsonView } from "@/components/ui/json-view";
import Link from "next/link";

async function fetchRun(id: string) {
  const res = await fetch(`http://localhost:8000/api/runs/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch run");
  return res.json();
}

async function fetchSpans(id: string) {
  const res = await fetch(`http://localhost:8000/api/runs/${id}/spans`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch spans");
  return res.json();
}

export default async function RunDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const [{ run }, { spans }] = await Promise.all([
    fetchRun(id),
    fetchSpans(id),
  ]);
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Run {id}</h1>
        <Link href="/runs" className="text-sm underline">
          Back
        </Link>
      </div>

      <div className="rounded border p-3">
        <div className="text-sm">status: {run.status}</div>
        <div className="text-sm">thread: {run.thread_id}</div>
      </div>

      <ReplayButton runId={id} />

      <div className="space-y-2">
        <h2 className="text-lg font-medium">Traces</h2>
        <div className="grid gap-2">
          {spans?.map((s: any) => {
            const dur =
              s.end_ts && s.start_ts ? (s.end_ts - s.start_ts) * 1000 : null;
            const req = s?.attrs?.request;
            const res = s?.attrs?.response;
            return (
              <div key={s.id} className="rounded border p-3">
                <div className="text-sm font-medium">
                  {s.kind}: {s.name}
                </div>
                <div className="text-xs text-muted-foreground">
                  node: {s.node_id || "-"} • fp: {s.fingerprint.slice(0, 10)}…
                  {dur !== null ? ` • ${dur.toFixed(1)}ms` : ""}
                  {s?.attrs?.status ? ` • ${s.attrs.status}` : ""}
                </div>
                {s?.kind === "node" &&
                (s?.attrs?.before_state || s?.attrs?.after_state) ? (
                  <details className="mt-2">
                    <summary className="text-xs cursor-pointer">state</summary>
                    {s?.attrs?.before_state ? (
                      <div className="mt-1">
                        <div className="text-xs font-semibold">before</div>
                        <JsonView value={s.attrs.before_state} />
                      </div>
                    ) : null}
                    {s?.attrs?.after_state ? (
                      <div className="mt-2">
                        <div className="text-xs font-semibold">after</div>
                        <JsonView value={s.attrs.after_state} />
                      </div>
                    ) : null}
                  </details>
                ) : null}
                {req ? (
                  <details className="mt-2">
                    <summary className="text-xs cursor-pointer">
                      request
                    </summary>
                    <JsonView value={req} />
                  </details>
                ) : null}
                {res ? (
                  <details className="mt-2">
                    <summary className="text-xs cursor-pointer">
                      response
                    </summary>
                    <JsonView value={res} />
                  </details>
                ) : null}
                {/* Only show raw attrs when there's no structured state or req/resp */}
                {!req &&
                !res &&
                !(
                  s?.kind === "node" &&
                  (s?.attrs?.before_state || s?.attrs?.after_state)
                ) ? (
                  <JsonView value={s.attrs} />
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
