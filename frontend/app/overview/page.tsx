"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getSwotOverview } from "@/lib/api/swot";
import type { SwotOverview } from "@/lib/api/types";
import styles from "./overview.module.css";

type Finding = SwotOverview["strengths"][number];

const QUADRANTS: {
  key: "strengths" | "weaknesses" | "opportunities" | "threats";
  title: string;
}[] = [
  { key: "strengths", title: "Strengths" },
  { key: "weaknesses", title: "Weaknesses" },
  { key: "opportunities", title: "Opportunities" },
  { key: "threats", title: "Threats" },
];

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString("en-CA", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function FindingItem({ f }: { f: Finding }) {
  return (
    <li className={styles.item}>
      <div className={styles.itemMain}>
        <span className={styles.bulletText}>{f.text}</span>
        <Link href={`/competitors/${f.competitorId}`} className={styles.tag}>
          {f.competitorName}
        </Link>
      </div>
      {(f.isNew || f.isChanged) && (
        <div className={styles.badges}>
          {f.isNew ? (
            <span className={`${styles.badge} ${styles.new}`}>New</span>
          ) : null}
          {f.isChanged ? (
            <span className={`${styles.badge} ${styles.changed}`}>Changed</span>
          ) : null}
        </div>
      )}
      <details className={styles.sources}>
        <summary>Sources</summary>
        <div className={styles.sourceBody}>
          <a
            href={f.sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className={styles.link}
          >
            {f.sourceLabel}
          </a>
          <span className={styles.sourceMeta}>{formatDate(f.detectedAt)}</span>
        </div>
      </details>
    </li>
  );
}

export default function OverviewPage() {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["swot-overview"],
    queryFn: getSwotOverview,
  });

  if (isLoading) {
    return <p className={styles.state}>Loading SWOT overview…</p>;
  }

  if (isError || !data) {
    return (
      <div className={styles.state} role="alert">
        <p>
          Couldn’t load the SWOT overview:{" "}
          {(error as Error)?.message ?? "unknown error"}.
        </p>
        <button className={styles.retry} onClick={() => refetch()}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <main className={styles.page}>
      <header>
        <h1 className={styles.title}>SWOT overview</h1>
        <p className={styles.sub}>
          Findings across all tracked competitors · last updated{" "}
          {data.updatedAt ? formatDate(data.updatedAt) : "Not yet"}
        </p>
      </header>

      <div className={styles.grid}>
        {QUADRANTS.map(({ key, title }) => {
          const items = data[key];
          return (
            <section
              key={key}
              className={`${styles.quadrant} ${styles[key]}`}
              aria-labelledby={`${key}-heading`}
            >
              <div className={styles.qHead}>
                <h2 id={`${key}-heading`}>{title}</h2>
                <span className={styles.count}>{items.length}</span>
              </div>
              {items.length === 0 ? (
                <p className={styles.empty}>No findings yet.</p>
              ) : (
                <ul className={styles.list}>
                  {items.map((f) => (
                    <FindingItem key={f.id} f={f} />
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
    </main>
  );
}
