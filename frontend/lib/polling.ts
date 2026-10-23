import type { CompetitorProfile, CompetitorSummary, AgentRun } from "@/lib/api/types";

const POLL_MS = 3000;

function isInProgress(status: string | undefined): boolean {
  return status === "pending" || status === "running";
}

/** Poll while any competitor research is still pending/running. */
export function competitorsPollInterval(
  competitors: CompetitorSummary[] | undefined,
): number | false {
  if (!competitors?.some((c) => isInProgress(c.researchStatus))) return false;
  return POLL_MS;
}

/** Poll while this profile's research is still pending/running. */
export function profilePollInterval(
  profile: CompetitorProfile | undefined,
): number | false {
  if (!profile || !isInProgress(profile.researchStatus)) return false;
  return POLL_MS;
}

/** Poll while any agent run is still pending/running. */
export function runsPollInterval(runs: AgentRun[] | undefined): number | false {
  if (!runs?.some((r) => isInProgress(r.status))) return false;
  return POLL_MS;
}
