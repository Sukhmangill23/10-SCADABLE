"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { getSwotOverview } from "@/lib/api/swot";
import type { SwotOverview } from "@/lib/api/types";
import styles from "./overview.module.css";

// Derived from the existing type so we don't depend on its exported name.
type Finding = SwotOverview["strengths"][number];

const QUADRANTS: {
  key: "strengths" | "weaknesses" | "opportunities" | "threats";
  title: string;
  hint: string;
}[] = [
  { key: "strengths", title: "Strengths", hint: "Where competitors are strong" },
  { key: "weaknesses", title: "Weaknesses", hint: "Where competitors fall short" },
  { key: "opportunities", title: "Opportunities", hint: "Gaps SCADABLE can use" },
  { key: "threats", title: "Threats", hint: "Moves that could hurt SCADABLE" },
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
      <p className={styles.text}>
        {f.text}
        {f.isNew && <span className={`${styles.badge} ${styles.new}`}>New</span>}
        {f.isChanged && (
          <span className={`${styles.badge} ${styles.changed}`}>Changed</span>
        )}
      </p>
      <p className={styles.meta}>
        <Link href={`/competitors/${f.competitorId}`} className={styles.link}>
          {f.competitorName}
        </Link>
        {" · "}
        <a
          href={f.sourceUrl}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.link}
        >
          {f.sourceLabel}
        </a>
        {" · "}
        {formatDate(f.detectedAt)}
      </p>
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
          Findings across all tracked competitors. Last updated{" "}
          {data.updatedAt ? formatDate(data.updatedAt) : "Not yet"}
        </p>
      </header>

      <div className={styles.grid}>
        {QUADRANTS.map(({ key, title, hint }) => {
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
              <p className={styles.hint}>{hint}</p>
              {items.length === 0 ? (
                <p className={styles.empty}>
                  Nothing here yet. Research a competitor to add findings.
                </p>
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
