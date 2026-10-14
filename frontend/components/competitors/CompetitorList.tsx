"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { competitorsApi, type CompetitorSummary, type Trend } from "@/lib/api";
import styles from "./CompetitorList.module.css";

type ActivityFilter = "all" | Trend;

const FILTERS: { id: ActivityFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "up", label: "Active" },
  { id: "flat", label: "Stable" },
  { id: "down", label: "Quiet" },
];

const TREND_LABEL: Record<Trend, string> = {
  up: "↑ More active",
  down: "↓ Less active",
  flat: "— Stable",
};

function trendClass(trend: Trend): string {
  if (trend === "up") return styles.trendUp;
  if (trend === "down") return styles.trendDown;
  return styles.trendFlat;
}

/** Display host only, matching the mockup (no https://). */
function displayWebsite(website: string): string {
  return website.replace(/^https?:\/\//, "");
}

/** Simple relative time for mock timestamps (good enough for the list UI). */
function formatLastChecked(iso: string | null): string {
  if (!iso) return "Not checked";

  const then = new Date(iso).getTime();
  const now = Date.now();
  const days = Math.max(0, Math.floor((now - then) / (1000 * 60 * 60 * 24)));

  if (days === 0) return "Today";
  if (days === 1) return "1 day ago";
  return `${days} days ago`;
}

function matchesSearch(competitor: CompetitorSummary, query: string): boolean {
  if (!query) return true;
  const q = query.toLowerCase();
  return (
    competitor.name.toLowerCase().includes(q) ||
    displayWebsite(competitor.website).toLowerCase().includes(q)
  );
}

export function CompetitorList() {
  const [filter, setFilter] = useState<ActivityFilter>("all");
  const [search, setSearch] = useState("");

  const { data, isPending, isError, error } = useQuery({
    queryKey: ["competitors"],
    queryFn: () => competitorsApi.listCompetitors(),
  });

  const competitors = data ?? [];

  const visible = useMemo(() => {
    const query = search.trim();
    return competitors.filter((c) => {
      const matchesFilter = filter === "all" || c.trend === filter;
      return matchesFilter && matchesSearch(c, query);
    });
  }, [competitors, filter, search]);

  if (isPending) {
    return <p className={styles.status}>Loading competitors…</p>;
  }

  if (isError) {
    return (
      <p className={styles.status}>
        Could not load competitors
        {error instanceof Error ? `: ${error.message}` : "."}
      </p>
    );
  }

  return (
    <div className={styles.page}>
      <header className={styles.pageHead}>
        <h1>Competitors</h1>
        <p>
          Everyone you compete with, and how their activity is changing · sample
          data
        </p>
      </header>

      <div className={styles.listControls}>
        <div className={styles.filterTabs} role="group" aria-label="Filter competitors">
          {FILTERS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              aria-pressed={filter === tab.id}
              onClick={() => setFilter(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className={styles.searchGroup}>
          <label className={styles.searchWrap}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
              <circle cx="11" cy="11" r="6" />
              <path d="m16 16 4 4" strokeLinecap="round" />
            </svg>
            <input
              type="search"
              placeholder="Search by name..."
              aria-label="Search competitors"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </label>
          <span className={styles.resultCount}>
            {visible.length} of {competitors.length}
          </span>
        </div>
      </div>

      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.colName}>Name</th>
              <th className={styles.colWebsite}>Website</th>
              <th className={styles.colRelationship}>Relationship</th>
              <th className={styles.colActivity}>Activity</th>
              <th className={styles.colChecked}>Last checked</th>
              <th className={styles.colArrow} aria-hidden="true" />
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr className={styles.emptyRow}>
                <td colSpan={6}>No competitors match this view.</td>
              </tr>
            ) : (
              visible.map((c) => (
                <tr key={c.id}>
                  <td className={styles.companyCell}>{c.name}</td>
                  <td className={styles.websiteCell}>{displayWebsite(c.website)}</td>
                  <td>
                    <span className={styles.relationship}>Competitor</span>
                  </td>
                  <td>
                    <span className={`${styles.trend} ${trendClass(c.trend)}`}>
                      {TREND_LABEL[c.trend]}
                    </span>
                  </td>
                  <td className={styles.lastChecked}>
                    {formatLastChecked(c.lastResearchedAt)}
                  </td>
                  <td className={styles.rowArrow} aria-hidden="true">
                    <svg
                      viewBox="0 0 24 24"
                      width="13"
                      height="13"
                      fill="none"
                      stroke="currentColor"
                    >
                      <path
                        d="m9 5 7 7-7 7"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
