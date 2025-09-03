"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

type Run = { id: string; status: string; thread_id: string };

async function deleteRun(id: string) {
  const res = await fetch(`http://localhost:8000/api/runs/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete run");
  return res.json();
}

export function RunsList({ runs }: { runs: Run[] }) {
  const router = useRouter();

  return (
    <div className="grid gap-3">
      {runs?.map((r) => (
        <div
          key={r.id}
          className="flex items-center justify-between rounded border p-3 cursor-move"
          draggable
          onDragStart={(e) => {
            e.dataTransfer.setData("text/run-id", r.id);
            e.dataTransfer.effectAllowed = "move";
            (e.currentTarget as HTMLDivElement).classList.add("opacity-60");
          }}
          onDragEnd={(e) => {
            (e.currentTarget as HTMLDivElement).classList.remove("opacity-60");
          }}
        >
          <Link href={`/runs/${r.id}`} className="flex-1 hover:underline">
            <div className="text-sm font-medium">Run {r.id}</div>
            <div className="text-xs text-muted-foreground">
              status: {r.status} • thread: {r.thread_id}
            </div>
          </Link>
          <button
            className="ml-3 inline-flex items-center rounded bg-red-600 px-2.5 py-1.5 text-white text-xs"
            onClick={async () => {
              await deleteRun(r.id);
              router.refresh();
            }}
          >
            Delete
          </button>
        </div>
      ))}
    </div>
  );
}
