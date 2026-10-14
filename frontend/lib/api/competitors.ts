import { apiFetch, useMocks } from "@/lib/api/client";
import type {
  CompetitorProfile,
  CompetitorSummary,
  CreateCompetitorInput,
  CreateCompetitorResult,
} from "@/lib/api/types";
import { normalizeSourceUrl } from "@/lib/format";
import { mockCompetitors, mockProfiles } from "@/lib/mocks/data";

function delay(ms = 200) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function listCompetitors(): Promise<CompetitorSummary[]> {
  if (useMocks()) {
    await delay();
    // Return a new array so React Query sees a data change after mock mutations.
    return [...mockCompetitors];
  }
  return apiFetch<CompetitorSummary[]>("/competitors");
}

export async function getCompetitor(id: string): Promise<CompetitorProfile> {
  if (useMocks()) {
    await delay();
    const profile = mockProfiles[id];
    if (!profile) {
      const summary = mockCompetitors.find((c) => c.id === id);
      if (!summary) {
        throw new Error(`Competitor not found: ${id}`);
      }
      return {
        ...summary,
        summary: "Profile not researched yet.",
        findings: [],
        recentActivity: [],
        openRoles: null,
        nextRefreshAt: null,
        chartSeries: {
          scores: [],
          activityOverTime: [],
          signalsBySource: [],
          hiringTrend: [],
        },
      };
    }
    return profile;
  }
  return apiFetch<CompetitorProfile>(`/competitors/${id}`);
}

export async function createCompetitor(
  input: CreateCompetitorInput,
): Promise<CreateCompetitorResult> {
  if (useMocks()) {
    await delay();
    const sources = input.dataSources
      .map(normalizeSourceUrl)
      .filter(Boolean);
    if (!sources.length) {
      throw new Error("Add at least one data source");
    }

    const baseId = input.name.toLowerCase().replace(/\s+/g, "-") || "competitor";
    let id = baseId;
    let suffix = 2;
    while (
      mockCompetitors.some((c) => c.id === id) ||
      mockProfiles[id]
    ) {
      id = `${baseId}-${suffix}`;
      suffix += 1;
    }

    const competitor: CompetitorSummary = {
      id,
      name: input.name.trim(),
      website: sources[0],
      trend: "flat",
      researchStatus: "pending",
      lastResearchedAt: null,
      recentChangeSummary: null,
    };
    mockCompetitors.unshift(competitor);
    return {
      competitor,
      queuedRunId: `run-${id}-queued`,
    };
  }
  return apiFetch<CreateCompetitorResult>("/competitors", {
    method: "POST",
    body: input,
  });
}

export async function deleteCompetitor(id: string): Promise<void> {
  if (useMocks()) {
    await delay();
    const index = mockCompetitors.findIndex((c) => c.id === id);
    if (index === -1) {
      throw new Error(`Competitor not found: ${id}`);
    }
    mockCompetitors.splice(index, 1);
    delete mockProfiles[id];
    return;
  }
  await apiFetch<void>(`/competitors/${id}`, { method: "DELETE" });
}
