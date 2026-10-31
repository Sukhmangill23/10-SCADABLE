import { apiFetch, shouldUseMocks } from "@/lib/api/client";
import type { AgentRun } from "@/lib/api/types";
import { mockRuns } from "@/lib/mocks/data";

function delay(ms = 200) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function listRuns(): Promise<AgentRun[]> {
  if (shouldUseMocks()) {
    await delay();
    // Copy so React Query sees a stable snapshot after mock mutations.
    return [...mockRuns];
  }
  return apiFetch<AgentRun[]>("/runs");
}

export async function getRun(id: string): Promise<AgentRun> {
  if (shouldUseMocks()) {
    await delay();
    const run = mockRuns.find((r) => r.id === id);
    if (!run) {
      throw new Error(`Run not found: ${id}`);
    }
    return run;
  }
  return apiFetch<AgentRun>(`/runs/${id}`);
}
