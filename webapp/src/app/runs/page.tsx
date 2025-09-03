import { AppSidebar } from "@/components/app-sidebar";
import { RunsDndCompare } from "@/components/runs-dnd-compare";
import { RunsList } from "@/components/runs-list";
import { SiteHeader } from "@/components/site-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { revalidatePath } from "next/cache";

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
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <SiteHeader />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
              <div className="px-4 lg:px-6">
                <h1 className="text-2xl font-semibold">Runs</h1>
              </div>
              <div className="px-4 lg:px-6 grid gap-4 md:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Start new run</CardTitle>
                  </CardHeader>
                  <CardContent>
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
                  </CardContent>
                </Card>
                <RunsDndCompare runs={runs} />
              </div>
              <div className="px-4 lg:px-6">
                <Card>
                  <CardHeader>
                    <CardTitle>All runs</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <RunsList runs={runs} />
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
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
