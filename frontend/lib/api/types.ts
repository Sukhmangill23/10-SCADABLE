export type ResearchStatus = "pending" | "running" | "success" | "failed";

export type Trend = "up" | "flat" | "down";

export type SwotCategory = "strength" | "weakness" | "opportunity" | "threat";

export type SignalSource = "website" | "jobs" | "reviews" | "press";

export type Finding = {
  id: string;
  /** Null for overall SCADABLE SWOT findings that are not tied to one competitor. */
  competitorId: string | null;
  competitorName: string;
  category: SwotCategory;
  text: string;
  sourceUrl: string;
  sourceLabel: string;
  detectedAt: string;
  isNew?: boolean;
  isChanged?: boolean;
};

export type ChartPoint = {
  label: string;
  value: number;
};

export type ScoreSeries = {
  label: string;
  competitor: number;
  scadable: number | null;
};

export type ActivityItem = {
  id: string;
  text: string;
  detectedAt: string;
};

export type CompetitorSummary = {
  id: string;
  name: string;
  website: string;
  trend: Trend;
  researchStatus: ResearchStatus;
  lastResearchedAt: string | null;
  recentChangeSummary: string | null;
};

export type CompetitorProfile = CompetitorSummary & {
  summary: string;
  findings: Finding[];
  recentActivity: ActivityItem[];
  openRoles: number | null;
  nextRefreshAt: string | null;
  chartSeries: {
    scores: ScoreSeries[];
    activityOverTime: ChartPoint[];
    signalsBySource: ChartPoint[];
    hiringTrend: ChartPoint[];
  };
};

export type SwotOverview = {
  updatedAt: string | null;
  strengths: Finding[];
  weaknesses: Finding[];
  opportunities: Finding[];
  threats: Finding[];
};

export type CompanyProfile = {
  offerings: string[];
  positioningNotes: string[];
  github: {
    connected: boolean;
    repository: string | null;
    trackedFile: string | null;
    statusLabel: string;
    lastSyncedAt: string | null;
    recentChange: string | null;
  };
};

export type RunStep = {
  name: string;
  result: string;
  status: ResearchStatus;
};

export type AgentRun = {
  id: string;
  competitorId: string | null;
  competitorName: string;
  status: ResearchStatus;
  costUsd: number | null;
  stepCount: number;
  cacheHits: number | null;
  cacheMisses: number | null;
  startedAt: string;
  finishedAt: string | null;
  steps: RunStep[];
  pullRequestUrl: string | null;
  /** Present when status is failed; null/omitted otherwise. */
  errorMessage: string | null;
};

export type CreateCompetitorInput = {
  name: string;
  /** Website URL(s). UI sends a single link; backend stores the first as website. */
  dataSources: string[];
};

export type CreateCompetitorResult = {
  competitor: CompetitorSummary;
  queuedRunId: string;
};
