"use client";

import { DiffView } from "@/components/diff-view";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogBody,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useCallback, useMemo, useState } from "react";

type Run = { id: string; status: string; thread_id: string };

async function fetchDiff(left: string, right: string) {
  const params = new URLSearchParams({ left, right });
  const res = await fetch(`http://localhost:8000/api/runs/diff?${params}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch diff");
  return res.json();
}

export function RunsDndCompare({ runs }: { runs: Run[] }) {
  const [left, setLeft] = useState<string | null>(null);
  const [right, setRight] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [diff, setDiff] = useState<any | null>(null);
  const leftRun = useMemo(
    () => runs.find((r) => r.id === left) || null,
    [runs, left]
  );
  const rightRun = useMemo(
    () => runs.find((r) => r.id === right) || null,
    [runs, right]
  );

  const onDropZone = useCallback(
    (side: "left" | "right", e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      const id = e.dataTransfer.getData("text/run-id");
      if (!id) return;
      if (side === "left") setLeft(id);
      else setRight(id);
    },
    []
  );

  const onDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  }, []);

  const clear = useCallback(() => {
    setLeft(null);
    setRight(null);
    setDiff(null);
  }, []);

  const doDiff = useCallback(async () => {
    if (!left || !right || left === right) return;
    const d = await fetchDiff(left, right);
    setDiff(d);
    setOpen(true);
  }, [left, right]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Compare runs (drag and drop)</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div
            className="rounded border-2 border-dashed p-4 min-h-24 flex items-center justify-center text-sm"
            onDrop={(e) => onDropZone("left", e)}
            onDragOver={onDragOver}
          >
            {leftRun ? (
              <div className="text-center">
                <div className="font-medium">Left</div>
                <div className="font-mono text-xs">{leftRun.id}</div>
                <div className="text-xs text-muted-foreground">
                  status: {leftRun.status}
                </div>
              </div>
            ) : (
              <span className="text-muted-foreground">Drag a run here</span>
            )}
          </div>
          <div
            className="rounded border-2 border-dashed p-4 min-h-24 flex items-center justify-center text-sm"
            onDrop={(e) => onDropZone("right", e)}
            onDragOver={onDragOver}
          >
            {rightRun ? (
              <div className="text-center">
                <div className="font-medium">Right</div>
                <div className="font-mono text-xs">{rightRun.id}</div>
                <div className="text-xs text-muted-foreground">
                  status: {rightRun.status}
                </div>
              </div>
            ) : (
              <span className="text-muted-foreground">Drag a run here</span>
            )}
          </div>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <Button
            size="sm"
            onClick={doDiff}
            disabled={!left || !right || left === right}
          >
            Diff
          </Button>
          <Button size="sm" variant="outline" onClick={clear}>
            Clear
          </Button>
        </div>

        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent className="sm:max-w-6xl">
            <DialogHeader>
              <DialogTitle>Diff</DialogTitle>
            </DialogHeader>
            <DialogBody>
              {!diff ? (
                <div className="text-sm text-muted-foreground">
                  No diff loaded
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="text-sm">
                    Left:{" "}
                    <span className="font-mono">{diff?.left_run?.id}</span>
                    <br />
                    Right:{" "}
                    <span className="font-mono">{diff?.right_run?.id}</span>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    matched: {diff?.summary?.matched} • only-left:{" "}
                    {diff?.summary?.only_left} • only-right:{" "}
                    {diff?.summary?.only_right}
                  </div>
                  <div className="space-y-3 max-h-[70vh] overflow-auto pr-2">
                    {(diff?.matched || []).map((m: any, i: number) => (
                      <div
                        key={`${m.fingerprint}-${i}`}
                        className="rounded border p-3"
                      >
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
                            />
                            <DiffView
                              title="after_state"
                              left={m?.left?.attrs?.after_state}
                              right={m?.right?.attrs?.after_state}
                            />
                          </div>
                        ) : (
                          <div className="mt-2 grid gap-3">
                            <DiffView
                              title="request"
                              left={m?.left?.attrs?.request}
                              right={m?.right?.attrs?.request}
                            />
                            <DiffView
                              title="response"
                              left={m?.left?.attrs?.response}
                              right={m?.right?.attrs?.response}
                            />
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </DialogBody>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}
