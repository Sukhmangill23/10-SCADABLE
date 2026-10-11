import { apiFetch, useMocks } from "@/lib/api/client";
import type {
  CompetitorProfile,
  CompetitorSummary,
  CreateCompetitorInput,
  CreateCompetitorResult,
} from "@/lib/api/types";
import { mockCompetitors, mockProfiles } from "@/lib/mocks/data";

function delay(ms = 200) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function listCompetitors(): Promise<CompetitorSummary[]> {
  if (useMocks()) {
    await delay();
    return mockCompetitors;
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
    const id = input.name.toLowerCase().replace(/\s+/g, "-");
    const competitor: CompetitorSummary = {
      id,
      name: input.name.trim(),
      website: input.website.trim(),
      trend: "flat",
      researchStatus: "pending",
      lastResearchedAt: null,
      recentChangeSummary: null,
    };
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
