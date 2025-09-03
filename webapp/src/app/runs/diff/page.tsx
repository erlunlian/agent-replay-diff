import { DiffView } from "@/components/diff-view";
import Link from "next/link";

async function fetchDiff(left: string, right: string) {
  const params = new URLSearchParams({ left, right });
  const res = await fetch(`http://localhost:8000/api/runs/diff?${params}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch diff");
  return res.json();
}

export default async function RunsDiffPage({
  searchParams,
}: {
  searchParams: Promise<{ left?: string; right?: string; mode?: string }>;
}) {
  const { left, right, mode } = await searchParams;
  if (!left || !right) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <div className="text-sm">Missing left/right run ids</div>
        <Link href="/runs" className="text-sm underline">
          Back to runs
        </Link>
      </div>
    );
  }
  const diff = await fetchDiff(left, right);
  const matched = diff?.matched || [];
  const onlyLeft = diff?.only_left || [];
  const onlyRight = diff?.only_right || [];
  const viewMode = mode === "unified" ? "unified" : "split";

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Diff</h1>
        <Link href="/runs" className="text-sm underline">
          Back
        </Link>
      </div>

      <div className="rounded border p-3 text-sm">
        <div>
          Left: <span className="font-mono">{diff?.left_run?.id}</span>
        </div>
        <div>
          Right: <span className="font-mono">{diff?.right_run?.id}</span>
        </div>
        <div className="text-xs text-muted-foreground mt-1">
          matched: {diff?.summary?.matched} • only-left:{" "}
          {diff?.summary?.only_left} • only-right: {diff?.summary?.only_right}
        </div>
      </div>

      {onlyLeft?.length > 0 || onlyRight?.length > 0 ? (
        <div className="grid grid-cols-1 gap-3">
          {onlyLeft?.length > 0 ? (
            <div className="rounded border p-3">
              <div className="text-sm font-medium">Only in left</div>
              <div className="text-xs text-muted-foreground mb-2">
                {onlyLeft.length} unmatched spans
              </div>
              <div className="grid gap-2">
                {onlyLeft.map((s: any) => (
                  <div key={s.id} className="rounded border p-2">
                    <div className="text-xs">
                      {s.kind}: {s.name} • node: {s.node_id || "-"} • fp:{" "}
                      {String(s.fingerprint).slice(0, 10)}…
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          {onlyRight?.length > 0 ? (
            <div className="rounded border p-3">
              <div className="text-sm font-medium">Only in right</div>
              <div className="text-xs text-muted-foreground mb-2">
                {onlyRight.length} unmatched spans
              </div>
              <div className="grid gap-2">
                {onlyRight.map((s: any) => (
                  <div key={s.id} className="rounded border p-2">
                    <div className="text-xs">
                      {s.kind}: {s.name} • node: {s.node_id || "-"} • fp:{" "}
                      {String(s.fingerprint).slice(0, 10)}…
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="flex items-center justify-between">
        <div className="text-lg font-medium">Matched span diffs</div>
        <div className="text-xs">
          <Link
            href={`/runs/diff?left=${left}&right=${right}&mode=split`}
            className={
              "px-2 py-1 border rounded-l " +
              (viewMode === "split" ? "bg-accent" : "bg-white")
            }
          >
            Split
          </Link>
          <Link
            href={`/runs/diff?left=${left}&right=${right}&mode=unified`}
            className={
              "px-2 py-1 border rounded-r -ml-px " +
              (viewMode === "unified" ? "bg-accent" : "bg-white")
            }
          >
            Unified
          </Link>
        </div>
      </div>
      <div className="space-y-3">
        {matched?.length === 0 ? (
          <div className="text-sm text-muted-foreground">No matched spans</div>
        ) : null}
        {matched?.map((m: any, i: number) => {
          return (
            <div key={`${m.fingerprint}-${i}`} className="rounded border p-3">
              <div className="text-sm font-medium">
                {m.kind}: {m.name}
              </div>
              <div className="text-xs text-muted-foreground">
                node: {m.node_id || "-"} • fp:{" "}
                {String(m.fingerprint).slice(0, 10)}…
              </div>
              {m.kind === "node" ? (
                <div className="mt-2 grid gap-3">
                  <DiffView
                    title="before_state"
                    left={m?.left?.attrs?.before_state}
                    right={m?.right?.attrs?.before_state}
                    mode={viewMode as any}
                  />
                  <DiffView
                    title="after_state"
                    left={m?.left?.attrs?.after_state}
                    right={m?.right?.attrs?.after_state}
                    mode={viewMode as any}
                  />
                </div>
              ) : (
                <div className="mt-2 grid gap-3">
                  <DiffView
                    title="request"
                    left={m?.left?.attrs?.request}
                    right={m?.right?.attrs?.request}
                    mode={viewMode as any}
                  />
                  <DiffView
                    title="response"
                    left={m?.left?.attrs?.response}
                    right={m?.right?.attrs?.response}
                    mode={viewMode as any}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
