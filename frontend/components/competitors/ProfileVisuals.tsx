"use client";

import { useState } from "react";
import type { CompetitorProfile } from "@/lib/api";
import { ActivityChart } from "./ProfileCharts";
import styles from "./CompetitorProfile.module.css";

type VisualId = "scores" | "activity";

const VISUALS: { id: VisualId; title: string }[] = [
  { id: "scores", title: "Scores vs SCADABLE" },
  { id: "activity", title: "Activity over time" },
];

export function ProfileVisuals({
  chartSeries,
}: {
  chartSeries: CompetitorProfile["chartSeries"];
}) {
  const [active, setActive] = useState<VisualId>("activity");

  return (
    <section className={styles.card}>
      <h2>Visuals</h2>

      <div className={styles.visualTabs} role="tablist" aria-label="Profile charts">
        {VISUALS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active === tab.id}
            className={active === tab.id ? styles.visualTabActive : undefined}
            onClick={() => setActive(tab.id)}
          >
            {tab.title}
          </button>
        ))}
      </div>

      <div role="tabpanel" aria-label={VISUALS.find((v) => v.id === active)?.title}>
        {active === "scores" ? (
          <p className={styles.empty}>Scores vs SCADABLE — coming in D3.</p>
        ) : (
          <ActivityChart data={chartSeries.activityOverTime} />
        )}
      </div>
    </section>
  );
}
