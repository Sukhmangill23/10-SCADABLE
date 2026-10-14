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
    lastResearchedAt: "2026-10-10T14:00:00Z",
    recentChangeSummary: "Posted 4 new automation engineering roles",
  },
  {
    id: "orbit",
    name: "OrbitWorks",
    website: "https://orbitworks.example",
    trend: "up",
    researchStatus: "success",
    lastResearchedAt: "2026-10-11T11:00:00Z",
    recentChangeSummary: "Announced workflow automation product update",
  },
  {
    id: "harbor",
    name: "Harbor AI",
    website: "https://harborai.example",
    trend: "flat",
    researchStatus: "success",
    lastResearchedAt: "2026-10-08T09:00:00Z",
    recentChangeSummary: "Stable product messaging this cycle",
  },
  {
    id: "brightpath",
    name: "BrightPath",
    website: "https://brightpath.example",
    trend: "up",
    researchStatus: "success",
    lastResearchedAt: "2026-10-12T09:00:00Z",
    recentChangeSummary: "Expanded analytics integrations",
  },
  {
    id: "vertex",
    name: "Vertex Systems",
    website: "https://vertexsystems.example",
    trend: "flat",
    researchStatus: "success",
    lastResearchedAt: "2026-10-07T16:00:00Z",
    recentChangeSummary: "No major public changes this week",
  },
];

export const mockProfiles: Record<string, CompetitorProfile> = {
  northstar: {
    ...mockCompetitors[0],
    summary:
      "The competitor appears to be investing more heavily in automation. This could indicate a shift in product strategy and may affect how the partner positions its own features.",
    openRoles: 4,
    nextRefreshAt: "2026-10-18T14:00:00Z",
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
      {
        id: "f3",
        competitorId: "northstar",
        competitorName: "Northstar Labs",
        category: "opportunity",
        text: "Public roadmap emphasizes workflow automation updates",
        sourceUrl: "https://northstarlabs.example/blog/automation-update",
        sourceLabel: "Product blog",
        detectedAt: "2026-09-20T12:00:00Z",
      },
    ],
    recentActivity: [
      {
        id: "a1",
        text: "Announced a new automated analytics feature",
        detectedAt: "2026-10-06T12:00:00Z",
      },
      {
        id: "a2",
        text: "Added integrations with three new software platforms",
        detectedAt: "2026-09-29T12:00:00Z",
      },
      {
        id: "a3",
        text: "Posted four new AI and automation engineering roles",
        detectedAt: "2026-09-22T12:00:00Z",
      },
      {
        id: "a4",
        text: "Published a product update focused on workflow automation",
        detectedAt: "2026-09-12T12:00:00Z",
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
  orbit: {
    ...mockCompetitors[1],
    summary:
      "OrbitWorks is pushing workflow automation hard. Their public updates suggest they are racing to close the gap on execution tooling.",
    openRoles: 6,
    nextRefreshAt: "2026-10-18T11:00:00Z",
    findings: [
      {
        id: "o1",
        competitorId: "orbit",
        competitorName: "OrbitWorks",
        category: "threat",
        text: "Announced a major workflow automation product update",
        sourceUrl: "https://orbitworks.example/blog/workflow-update",
        sourceLabel: "Product blog",
        detectedAt: "2026-10-09T11:00:00Z",
        isNew: true,
      },
      {
        id: "o2",
        competitorId: "orbit",
        competitorName: "OrbitWorks",
        category: "strength",
        text: "Strong hiring signal across automation engineering",
        sourceUrl: "https://orbitworks.example/careers",
        sourceLabel: "Careers",
        detectedAt: "2026-10-08T10:00:00Z",
        isChanged: true,
      },
    ],
    recentActivity: [
      {
        id: "oa1",
        text: "Announced workflow automation product update",
        detectedAt: "2026-10-09T11:00:00Z",
      },
      {
        id: "oa2",
        text: "Opened six new roles across platform and AI teams",
        detectedAt: "2026-10-05T09:00:00Z",
      },
      {
        id: "oa3",
        text: "Updated pricing page with automation add-ons",
        detectedAt: "2026-09-28T15:00:00Z",
      },
    ],
    chartSeries: {
      scores: [
        { label: "Data collection", competitor: 7, scadable: 7 },
        { label: "Workflow execution", competitor: 8, scadable: 8 },
        { label: "Analytics", competitor: 6, scadable: 6 },
        { label: "AI recommendations", competitor: 7, scadable: 7 },
      ],
      activityOverTime: [
        { label: "W1", value: 1 },
        { label: "W2", value: 3 },
        { label: "W3", value: 2 },
        { label: "W4", value: 5 },
      ],
      signalsBySource: [
        { label: "website", value: 4 },
        { label: "jobs", value: 6 },
        { label: "reviews", value: 1 },
        { label: "press", value: 2 },
      ],
      hiringTrend: [
        { label: "Jul", value: 2 },
        { label: "Aug", value: 3 },
        { label: "Sep", value: 4 },
        { label: "Oct", value: 6 },
      ],
    },
  },
  harbor: {
    ...mockCompetitors[2],
    summary:
      "Harbor AI looks steady this cycle. Messaging is consistent and hiring is quiet, so they are less of an immediate threat than more active peers.",
    openRoles: 1,
    nextRefreshAt: "2026-10-20T09:00:00Z",
    findings: [
      {
        id: "h1",
        competitorId: "harbor",
        competitorName: "Harbor AI",
        category: "weakness",
        text: "Little public product movement compared with peers",
        sourceUrl: "https://harborai.example/product",
        sourceLabel: "Product page",
        detectedAt: "2026-10-08T09:00:00Z",
      },
      {
        id: "h2",
        competitorId: "harbor",
        competitorName: "Harbor AI",
        category: "opportunity",
        text: "Limited press coverage leaves room for SCADABLE positioning",
        sourceUrl: "https://harborai.example/news",
        sourceLabel: "Newsroom",
        detectedAt: "2026-10-01T09:00:00Z",
      },
    ],
    recentActivity: [
      {
        id: "ha1",
        text: "Refreshed homepage messaging with minor copy edits",
        detectedAt: "2026-10-02T09:00:00Z",
      },
      {
        id: "ha2",
        text: "No new roles posted this research cycle",
        detectedAt: "2026-09-25T09:00:00Z",
      },
    ],
    chartSeries: {
      scores: [
        { label: "Data collection", competitor: 6, scadable: 7 },
        { label: "Workflow execution", competitor: 5, scadable: 8 },
        { label: "Analytics", competitor: 7, scadable: 6 },
        { label: "AI recommendations", competitor: 8, scadable: 7 },
      ],
      activityOverTime: [
        { label: "W1", value: 1 },
        { label: "W2", value: 0 },
        { label: "W3", value: 1 },
        { label: "W4", value: 1 },
      ],
      signalsBySource: [
        { label: "website", value: 3 },
        { label: "jobs", value: 1 },
        { label: "reviews", value: 2 },
        { label: "press", value: 0 },
      ],
      hiringTrend: [
        { label: "Jul", value: 2 },
        { label: "Aug", value: 1 },
        { label: "Sep", value: 1 },
        { label: "Oct", value: 1 },
      ],
    },
  },
  brightpath: {
    ...mockCompetitors[3],
    summary:
      "BrightPath is expanding analytics integrations quickly. That makes them a rising peer on reporting depth even if workflow tooling still trails.",
    openRoles: 3,
    nextRefreshAt: "2026-10-19T09:00:00Z",
    findings: [
      {
        id: "b1",
        competitorId: "brightpath",
        competitorName: "BrightPath",
        category: "strength",
        text: "Expanded analytics integrations across three platforms",
        sourceUrl: "https://brightpath.example/integrations",
        sourceLabel: "Integrations",
        detectedAt: "2026-10-11T09:00:00Z",
        isNew: true,
      },
      {
        id: "b2",
        competitorId: "brightpath",
        competitorName: "BrightPath",
        category: "threat",
        text: "Marketing push around automated reporting",
        sourceUrl: "https://brightpath.example/blog/reporting",
        sourceLabel: "Product blog",
        detectedAt: "2026-10-10T09:00:00Z",
      },
    ],
    recentActivity: [
      {
        id: "ba1",
        text: "Launched three new analytics integrations",
        detectedAt: "2026-10-11T09:00:00Z",
      },
      {
        id: "ba2",
        text: "Published a reporting automation case study",
        detectedAt: "2026-10-04T09:00:00Z",
      },
      {
        id: "ba3",
        text: "Posted three open roles on the data platform team",
        detectedAt: "2026-09-27T09:00:00Z",
      },
    ],
    chartSeries: {
      scores: [
        { label: "Data collection", competitor: 7, scadable: 7 },
        { label: "Workflow execution", competitor: 4, scadable: 8 },
        { label: "Analytics", competitor: 9, scadable: 6 },
        { label: "AI recommendations", competitor: 5, scadable: 7 },
      ],
      activityOverTime: [
        { label: "W1", value: 2 },
        { label: "W2", value: 2 },
        { label: "W3", value: 3 },
        { label: "W4", value: 4 },
      ],
      signalsBySource: [
        { label: "website", value: 4 },
        { label: "jobs", value: 3 },
        { label: "reviews", value: 2 },
        { label: "press", value: 2 },
      ],
      hiringTrend: [
        { label: "Jul", value: 1 },
        { label: "Aug", value: 2 },
        { label: "Sep", value: 2 },
        { label: "Oct", value: 3 },
      ],
    },
  },
  vertex: {
    ...mockCompetitors[4],
    summary:
      "Vertex Systems remains steady with little public movement. Useful as a baseline peer, but not the loudest competitive signal this month.",
    openRoles: 2,
    nextRefreshAt: "2026-10-21T16:00:00Z",
    findings: [
      {
        id: "v1",
        competitorId: "vertex",
        competitorName: "Vertex Systems",
        category: "weakness",
        text: "No major public product changes detected this cycle",
        sourceUrl: "https://vertexsystems.example/product",
        sourceLabel: "Product page",
        detectedAt: "2026-10-07T16:00:00Z",
      },
      {
        id: "v2",
        competitorId: "vertex",
        competitorName: "Vertex Systems",
        category: "opportunity",
        text: "Quiet press presence compared with more active competitors",
        sourceUrl: "https://vertexsystems.example/news",
        sourceLabel: "Newsroom",
        detectedAt: "2026-10-06T16:00:00Z",
      },
    ],
    recentActivity: [
      {
        id: "va1",
        text: "Minor docs update on compliance workflows",
        detectedAt: "2026-10-03T16:00:00Z",
      },
      {
        id: "va2",
        text: "No significant hiring or product announcements",
        detectedAt: "2026-09-26T16:00:00Z",
      },
    ],
    chartSeries: {
      scores: [
        { label: "Data collection", competitor: 6, scadable: 7 },
        { label: "Workflow execution", competitor: 6, scadable: 8 },
        { label: "Analytics", competitor: 5, scadable: 6 },
        { label: "AI recommendations", competitor: 4, scadable: 7 },
      ],
      activityOverTime: [
        { label: "W1", value: 1 },
        { label: "W2", value: 1 },
        { label: "W3", value: 0 },
        { label: "W4", value: 1 },
      ],
      signalsBySource: [
        { label: "website", value: 2 },
        { label: "jobs", value: 2 },
        { label: "reviews", value: 1 },
        { label: "press", value: 0 },
      ],
      hiringTrend: [
        { label: "Jul", value: 2 },
        { label: "Aug", value: 2 },
        { label: "Sep", value: 2 },
        { label: "Oct", value: 2 },
      ],
    },
  },
};

export const mockSwot: SwotOverview = {
  updatedAt: "2026-10-08T12:00:00Z",
  strengths: [mockProfiles.northstar.findings[0]],
  weaknesses: [mockProfiles.harbor.findings[0]],
  opportunities: [mockProfiles.harbor.findings[1]],
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
