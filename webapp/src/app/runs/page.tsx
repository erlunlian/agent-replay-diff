import { revalidatePath } from "next/cache";
import Link from "next/link";

async function fetchRuns() {
  const res = await fetch(`http://localhost:8000/api/runs`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch runs");
  const data = await res.json();
  return data.runs as any[];
}

async function startRun() {
  const res = await fetch(`http://localhost:8000/api/runs/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ max_steps: 5 }),
  });
  return res.json();
}

async function diffRuns(left: string, right: string) {
  const params = new URLSearchParams({ left, right });
  const res = await fetch(`http://localhost:8000/api/runs/diff?${params}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to diff runs");
  return res.json();
}

async function deleteRun(id: string) {
  const res = await fetch(`http://localhost:8000/api/runs/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete run");
  return res.json();
}

export default async function RunsPage() {
  const runs = await fetchRuns();
  return (
    <div className="container mx-auto p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Runs</h1>
      <form
        action={async () => {
          "use server";
          await startRun();
          revalidatePath("/runs");
        }}
      >
        <button className="inline-flex items-center rounded bg-black px-3 py-1.5 text-white text-sm">
          Start run
        </button>
      </form>
      <CompareForm runs={runs} />
      <div className="grid gap-3">
        {runs?.map((r) => (
          <div key={r.id} className="flex items-center justify-between rounded border p-3">
            <Link href={`/runs/${r.id}`} className="flex-1 hover:underline">
              <div className="text-sm font-medium">Run {r.id}</div>
              <div className="text-xs text-muted-foreground">
                status: {r.status} • thread: {r.thread_id}
              </div>
            </Link>
            <form
              action={async () => {
                "use server";
                await deleteRun(r.id);
                revalidatePath("/runs");
              }}
            >
              <button className="ml-3 inline-flex items-center rounded bg-red-600 px-2.5 py-1.5 text-white text-xs">
                Delete
              </button>
            </form>
          </div>
        ))}
      </div>
    </div>
  );
}

function CompareForm({ runs }: { runs: any[] }) {
  return (
    <form
      action={async (formData) => {
        "use server";
        const left = String(formData.get("left") || "");
        const right = String(formData.get("right") || "");
        if (!left || !right || left === right) return;
        // Trigger a diff by redirecting to the new page
      }}
      className="rounded border p-3 space-y-3"
    >
      <div className="text-sm font-medium">Compare two runs</div>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 items-center">
        <select name="left" className="border rounded px-2 py-1 text-sm">
          <option value="">Select left run…</option>
          {runs?.map((r) => (
            <option key={r.id} value={r.id}>
              {r.id}
            </option>
          ))}
        </select>
        <span className="text-center text-xs text-muted-foreground">vs</span>
        <select name="right" className="border rounded px-2 py-1 text-sm">
          <option value="">Select right run…</option>
          {runs?.map((r) => (
            <option key={r.id} value={r.id}>
              {r.id}
            </option>
          ))}
        </select>
      </div>
      <DiffSubmit />
    </form>
  );
}

function DiffSubmit() {
  return (
    <button
      formAction={async (formData) => {
        "use server";
        const left = String(formData.get("left") || "");
        const right = String(formData.get("right") || "");
        if (!left || !right || left === right) return;
        // Use Next.js redirect to diff page
        const { redirect } = await import("next/navigation");
        redirect(`/runs/diff?left=${left}&right=${right}`);
      }}
      className="inline-flex items-center rounded bg-black px-3 py-1.5 text-white text-sm"
    >
      Diff runs
    </button>
  );
}
