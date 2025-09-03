"use client";

import { useMemo } from "react";

type Mode = "split" | "unified";

function stableSortKeys(value: any): any {
  if (Array.isArray(value)) {
    return value.map((v) => stableSortKeys(v));
  }
  if (value && typeof value === "object") {
    const out: Record<string, any> = {};
    for (const key of Object.keys(value).sort()) {
      out[key] = stableSortKeys(value[key]);
    }
    return out;
  }
  return value;
}

function toPrettyJSON(value: any): string {
  if (value === undefined) return "";
  try {
    return JSON.stringify(stableSortKeys(value), null, 2);
  } catch {
    try {
      return JSON.stringify(value, null, 2);
    } catch {
      return String(value);
    }
  }
}

type Op =
  | { type: "context"; left: string; right: string }
  | { type: "del"; left: string }
  | { type: "add"; right: string };

function computeOps(leftText: string, rightText: string): Op[] {
  const a = leftText.split("\n");
  const b = rightText.split("\n");
  const m = a.length;
  const n = b.length;
  const lcs: number[][] = Array.from({ length: m + 1 }, () =>
    Array.from({ length: n + 1 }, () => 0)
  );
  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      if (a[i] === b[j]) lcs[i][j] = lcs[i + 1][j + 1] + 1;
      else lcs[i][j] = Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }
  const ops: Op[] = [];
  let i = 0,
    j = 0;
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      ops.push({ type: "context", left: a[i], right: b[j] });
      i++;
      j++;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      ops.push({ type: "del", left: a[i] });
      i++;
    } else {
      ops.push({ type: "add", right: b[j] });
      j++;
    }
  }
  while (i < m) {
    ops.push({ type: "del", left: a[i++] });
  }
  while (j < n) {
    ops.push({ type: "add", right: b[j++] });
  }
  return ops;
}

type Row = {
  type: "context" | "add" | "del" | "change";
  left?: string;
  right?: string;
};

function opsToSplitRows(ops: Op[]): Row[] {
  const rows: Row[] = [];
  for (const op of ops) {
    if (op.type === "context") {
      rows.push({ type: "context", left: op.left, right: op.right });
    } else if (op.type === "del") {
      rows.push({ type: "del", left: op.left, right: "" });
    } else {
      const prev = rows[rows.length - 1];
      if (prev && prev.type === "del" && !prev.right) {
        prev.type = "change";
        prev.right = op.right;
      } else {
        rows.push({ type: "add", left: "", right: op.right });
      }
    }
  }
  return rows;
}

export function DiffView({
  title,
  left,
  right,
  mode = "split",
}: {
  title: string;
  left: any;
  right: any;
  mode?: Mode;
}) {
  const leftText = useMemo(() => toPrettyJSON(left), [left]);
  const rightText = useMemo(() => toPrettyJSON(right), [right]);
  const ops = useMemo(
    () => computeOps(leftText, rightText),
    [leftText, rightText]
  );
  const splitRows = useMemo(() => opsToSplitRows(ops), [ops]);
  const hasChanges = ops.some((o) => o.type !== "context");

  return (
    <div className="rounded border">
      <div className="px-3 py-2 border-b text-sm font-medium flex items-center justify-between">
        <span>{title}</span>
        <span className="text-xs text-muted-foreground">
          {hasChanges ? "changes" : "no changes"}
        </span>
      </div>
      {mode === "split" ? (
        <div className="grid grid-cols-2 text-xs">
          <div className="border-r">
            {splitRows.map((r, idx) => (
              <pre
                key={idx}
                className={
                  "px-3 py-0.5 whitespace-pre-wrap " +
                  (r.type === "del" || r.type === "change"
                    ? "bg-red-50 text-red-700"
                    : r.type === "add"
                    ? "bg-white"
                    : "bg-white")
                }
              >
                {r.left}
              </pre>
            ))}
          </div>
          <div>
            {splitRows.map((r, idx) => (
              <pre
                key={idx}
                className={
                  "px-3 py-0.5 whitespace-pre-wrap " +
                  (r.type === "add" || r.type === "change"
                    ? "bg-green-50 text-green-700"
                    : r.type === "del"
                    ? "bg-white"
                    : "bg-white")
                }
              >
                {r.right}
              </pre>
            ))}
          </div>
        </div>
      ) : (
        <div className="text-xs">
          {ops.map((o, idx) => (
            <pre
              key={idx}
              className={
                "px-3 py-0.5 whitespace-pre-wrap " +
                (o.type === "add"
                  ? "bg-green-50 text-green-700"
                  : o.type === "del"
                  ? "bg-red-50 text-red-700"
                  : "bg-white")
              }
            >
              {o.type === "add"
                ? "+ " + (o as any).right
                : o.type === "del"
                ? "- " + (o as any).left
                : "  " + (o as any).left}
            </pre>
          ))}
        </div>
      )}
    </div>
  );
}
