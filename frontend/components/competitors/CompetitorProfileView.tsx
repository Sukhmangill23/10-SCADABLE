"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { competitorsApi, type Finding, type Trend } from "@/lib/api";
import {
  displayWebsite,
  formatRelativeFuture,
  formatRelativePast,
} from "@/lib/format";
import { ProfileVisuals } from "./ProfileVisuals";
import styles from "./CompetitorProfile.module.css";

const TREND_LABEL: Record<Trend, string> = {
  up: "↑ More active",
  down: "↓ Less active",
  flat: "— Stable",
};

/** Longer labels for the score list; chart keeps shorter series labels. */
const SCORE_LIST_LABELS: Record<string, string> = {
  "Data collection": "Automated data collection",
  "Workflow execution": "Automated workflow execution",
  Analytics: "Analytics & reporting",
  "AI recommendations": "AI-generated recommendations",
};

function trendClass(trend: Trend): string {
  if (trend === "up") return styles.trendUp;
  if (trend === "down") return styles.trendDown;
  return styles.trendFlat;
}

function uniqueSources(findings: Finding[]) {
  const seen = new Set<string>();
  const sources: { label: string; url: string }[] = [];

  for (const finding of findings) {
    const key = finding.sourceUrl;
    if (seen.has(key)) continue;
    seen.add(key);
    sources.push({ label: finding.sourceLabel, url: finding.sourceUrl });
  }

  return sources;
}

export function CompetitorProfileView({ id }: { id: string }) {
  const { data, isPending, isError, error } = useQuery({
    queryKey: ["competitor", id],
    queryFn: () => competitorsApi.getCompetitor(id),
  });

  const sources = useMemo(
    () => (data ? uniqueSources(data.findings) : []),
    [data],
  );

  if (isPending) {
    return <p className={styles.status}>Loading profile…</p>;
  }

  if (isError || !data) {
    return (
      <p className={styles.status}>
        Could not load profile
        {error instanceof Error ? `: ${error.message}` : "."}
      </p>
    );
  }

  return (
    <div className={styles.page}>
      <Link href="/competitors" className={styles.back}>
        ← Back to competitors
      </Link>

      <header className={styles.hero}>
        <div>
          <h1>{data.name}</h1>
          <p>{displayWebsite(data.website)}</p>
        </div>
        <span className={styles.pill}>Competitor</span>
      </header>

      <div className={styles.grid}>
        <div>
          <section className={styles.card}>
            <h2>Feature & automation score</h2>
            {data.chartSeries.scores.length === 0 ? (
              <p className={styles.empty}>Scores not researched yet.</p>
            ) : (
              data.chartSeries.scores.map((row) => (
                <div key={row.label} className={styles.featureRow}>
                  <span>{SCORE_LIST_LABELS[row.label] ?? row.label}</span>
                  <span className={styles.score}>{row.competitor}/10</span>
                </div>
              ))
            )}
          </section>

          <ProfileVisuals chartSeries={data.chartSeries} />

          <section className={styles.card}>
            <h2>
              Recent activity
              <span className={styles.cardSubtitle}>(sample data)</span>
            </h2>
            {data.recentActivity.length === 0 ? (
              <p className={styles.empty}>No recent activity yet.</p>
            ) : (
              data.recentActivity.map((item) => (
                <div key={item.id} className={styles.newsItem}>
                  {item.text}
                  <span className={styles.newsDate}>
                    {formatRelativePast(item.detectedAt)}
                  </span>
                </div>
              ))
            )}
          </section>
        </div>

        <div>
          <section className={styles.card}>
            <h2>At a glance</h2>
            <div className={styles.statRow}>
              <span>Trend</span>
              <b>
                <span className={`${styles.trend} ${trendClass(data.trend)}`}>
                  {TREND_LABEL[data.trend]}
                </span>
              </b>
            </div>
            <div className={styles.statRow}>
              <span>Open roles</span>
              <b>{data.openRoles ?? "—"}</b>
            </div>
            <div className={styles.statRow}>
              <span>Last checked</span>
              <b>{formatRelativePast(data.lastResearchedAt)}</b>
            </div>
            <div className={styles.statRow}>
              <span>Next refresh</span>
              <b>{formatRelativeFuture(data.nextRefreshAt)}</b>
            </div>
          </section>

          <section className={styles.card}>
            <h2>Why it matters</h2>
            <p className={styles.summary}>{data.summary}</p>
          </section>

          <section className={styles.card}>
            <h2>Sources</h2>
            {sources.length === 0 ? (
              <p className={styles.empty}>No sources linked yet.</p>
            ) : (
              <ul className={styles.sourceList}>
                {sources.map((source) => (
                  <li key={source.url}>
                    <a href={source.url} target="_blank" rel="noreferrer">
                      <span>{source.label}</span>
                      <span className={styles.sourceHost}>
                        {displayWebsite(source.url)}
                      </span>
                    </a>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
