import type {
  AgentRun,
  CompanyProfile,
  CompetitorProfile,
  CompetitorSummary,
  SwotOverview,
} from "@/lib/api/types";

export const mockCompetitors: CompetitorSummary[] = [
  {
    id: "northstar",
    name: "Northstar Labs",
    website: "https://northstarlabs.example",
    trend: "up",
    researchStatus: "success",
    lastResearchedAt: "2026-10-07T14:00:00Z",
    recentChangeSummary: "Posted 4 new automation engineering roles",
  },
  {
    id: "orbit",
    name: "OrbitWorks",
    website: "https://orbitworks.example",
    trend: "up",
    researchStatus: "success",
    lastResearchedAt: "2026-10-08T11:00:00Z",
    recentChangeSummary: "Announced workflow automation product update",
  },
  {
    id: "brightpath",
    name: "BrightPath",
    website: "https://brightpath.example",
    trend: "flat",
    researchStatus: "failed",
    lastResearchedAt: "2026-10-08T09:00:00Z",
    recentChangeSummary: null,
  },
  {
    id: "harbor",
    name: "Harbor AI",
    website: "https://harborai.example",
    trend: "flat",
    researchStatus: "pending",
    lastResearchedAt: null,
    recentChangeSummary: null,
  },
];

export const mockProfiles: Record<string, CompetitorProfile> = {
  northstar: {
    ...mockCompetitors[0],
    summary:
      "Compliance automation vendor investing heavily in AI-assisted workflows.",
    openRoles: 4,
    nextRefreshAt: "2026-10-14T14:00:00Z",
    findings: [
      {
        id: "f1",
        competitorId: "northstar",
        competitorName: "Northstar Labs",
        category: "strength",
        text: "Strong automation capabilities compared with tracked competitors",
        sourceUrl: "https://northstarlabs.example/product",
        sourceLabel: "Product page",
        detectedAt: "2026-10-07T14:00:00Z",
        isNew: true,
      },
      {
        id: "f2",
        competitorId: "northstar",
        competitorName: "Northstar Labs",
        category: "threat",
        text: "Hiring surge in AI and automation engineering roles",
        sourceUrl: "https://northstarlabs.example/careers",
        sourceLabel: "Careers",
        detectedAt: "2026-10-07T14:00:00Z",
        isChanged: true,
      },
    ],
    chartSeries: {
      scores: [
        { label: "Data collection", competitor: 8, scadable: 7 },
        { label: "Workflow execution", competitor: 5, scadable: 8 },
        { label: "Analytics", competitor: 9, scadable: 6 },
        { label: "AI recommendations", competitor: 6, scadable: 7 },
      ],
      activityOverTime: [
        { label: "W1", value: 2 },
        { label: "W2", value: 1 },
        { label: "W3", value: 4 },
        { label: "W4", value: 3 },
      ],
      signalsBySource: [
        { label: "website", value: 5 },
        { label: "jobs", value: 4 },
        { label: "reviews", value: 2 },
        { label: "press", value: 1 },
      ],
      hiringTrend: [
        { label: "Jul", value: 1 },
        { label: "Aug", value: 2 },
        { label: "Sep", value: 2 },
        { label: "Oct", value: 4 },
      ],
    },
  },
};

export const mockSwot: SwotOverview = {
  updatedAt: "2026-10-08T12:00:00Z",
  strengths: [mockProfiles.northstar.findings[0]],
  weaknesses: [],
  opportunities: [],
  threats: [mockProfiles.northstar.findings[1]],
};

export const mockCompany: CompanyProfile = {
  offerings: [
    "Automated competitor monitoring across multiple sources",
    "AI-assisted analysis of competitor activity",
    "Continuous tracking of product, hiring, and company updates",
  ],
  positioningNotes: [
    "Designed to reduce manual competitor research",
    "Turns competitor activity into actionable insights",
  ],
  github: {
    connected: false,
    repository: null,
    trackedFile: null,
    statusLabel: "Not connected",
    lastSyncedAt: null,
    recentChange: null,
  },
};

export const mockRuns: AgentRun[] = [
  {
    id: "run-northstar-1",
    competitorId: "northstar",
    competitorName: "Northstar Labs",
    status: "success",
    costUsd: 0.06,
    stepCount: 6,
    cacheHits: 4,
    cacheMisses: 2,
    startedAt: "2026-10-08T12:00:00Z",
    finishedAt: "2026-10-08T12:02:00Z",
    pullRequestUrl: null,
    steps: [
      { name: "Fetch careers page", result: "Cache hit", status: "success" },
      { name: "Fetch product updates", result: "Cache miss", status: "success" },
      {
        name: "Generate competitor summary",
        result: "Cache miss",
        status: "success",
      },
      {
        name: "Update competitor profile",
        result: "Success",
        status: "success",
      },
    ],
  },
  {
    id: "run-brightpath-1",
    competitorId: "brightpath",
    competitorName: "BrightPath",
    status: "failed",
    costUsd: 0.01,
    stepCount: 4,
    cacheHits: 2,
    cacheMisses: 2,
    startedAt: "2026-10-08T09:00:00Z",
    finishedAt: "2026-10-08T09:01:00Z",
    pullRequestUrl: null,
    steps: [
      {
        name: "Load tracked research categories",
        result: "Cache hit",
        status: "success",
      },
      { name: "Fetch careers page", result: "Cache miss", status: "success" },
      {
        name: "Generate competitor summary",
        result: "Failed",
        status: "failed",
      },
    ],
  },
];
