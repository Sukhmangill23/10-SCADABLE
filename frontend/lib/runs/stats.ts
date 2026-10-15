import type { AgentRun } from "@/lib/api/types";

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

export type WeeklyRunStats = {
  runsThisWeek: number;
  successful: number;
  estimatedCostUsd: number;
  cacheHitRatePct: number;
};

/** Runs started in the last 7 days (weekly totals for the summary cards). */
export function filterRunsThisWeek(
  runs: AgentRun[],
  now = Date.now(),
): AgentRun[] {
  const cutoff = now - WEEK_MS;
  return runs.filter((run) => new Date(run.startedAt).getTime() >= cutoff);
}

/**
 * One row per competitor: their most recent run.
 * Used for the Agent Runs table (not the full weekly history).
 */
export function latestRunPerCompetitor(runs: AgentRun[]): AgentRun[] {
  const sorted = [...runs].sort(
    (a, b) =>
      new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime(),
  );

  const latest = new Map<string, AgentRun>();
  for (const run of sorted) {
    const key = run.competitorId ?? run.competitorName;
    if (!latest.has(key)) {
      latest.set(key, run);
    }
  }

  return [...latest.values()];
}

export function computeWeeklyRunStats(runs: AgentRun[]): WeeklyRunStats {
  const week = filterRunsThisWeek(runs);
  const successful = week.filter((r) => r.status === "success").length;
  const estimatedCostUsd = week.reduce((sum, r) => sum + (r.costUsd ?? 0), 0);
  const hits = week.reduce((sum, r) => sum + (r.cacheHits ?? 0), 0);
  const misses = week.reduce((sum, r) => sum + (r.cacheMisses ?? 0), 0);
  const total = hits + misses;

  return {
    runsThisWeek: week.length,
    successful,
    estimatedCostUsd,
    cacheHitRatePct: total === 0 ? 0 : Math.round((hits / total) * 100),
  };
}

export function formatRunStatus(status: AgentRun["status"]): string {
  if (status === "success") return "Success";
  if (status === "failed") return "Failed";
  if (status === "running") return "Running";
  return "Pending";
}

export function formatRunCost(costUsd: number | null): string {
  if (costUsd == null) return "—";
  return `$${costUsd.toFixed(2)}`;
}

export function formatCacheStat(
  hits: number | null,
  misses: number | null,
): { hitsLabel: string; missesLabel: string } | null {
  if (hits == null || misses == null) return null;
  const hitsLabel = hits === 1 ? "1 hit" : `${hits} hits`;
  const missesLabel = misses === 1 ? "1 miss" : `${misses} misses`;
  return { hitsLabel, missesLabel };
}
