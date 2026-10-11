import { apiFetch, useMocks } from "@/lib/api/client";
import type { SwotOverview } from "@/lib/api/types";
import { mockSwot } from "@/lib/mocks/data";

export async function getSwotOverview(): Promise<SwotOverview> {
  if (useMocks()) {
    return mockSwot;
  }
  return apiFetch<SwotOverview>("/swot/overview");
}
