import { apiFetch, useMocks } from "@/lib/api/client";
import type { AgentRun } from "@/lib/api/types";
import { mockRuns } from "@/lib/mocks/data";

export async function listRuns(): Promise<AgentRun[]> {
  if (useMocks()) {
    return mockRuns;
  }
  return apiFetch<AgentRun[]>("/runs");
}

export async function getRun(id: string): Promise<AgentRun> {
  if (useMocks()) {
    const run = mockRuns.find((r) => r.id === id);
    if (!run) {
      throw new Error(`Run not found: ${id}`);
    }
    return run;
  }
  return apiFetch<AgentRun>(`/runs/${id}`);
}
