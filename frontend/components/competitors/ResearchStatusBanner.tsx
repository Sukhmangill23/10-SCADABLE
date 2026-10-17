"use client";

import { Button } from "@/components/ui/Button";
import type { ResearchStatus } from "@/lib/api";
import styles from "./CompetitorProfile.module.css";

type Props = {
  status: ResearchStatus;
  competitorName: string;
  rerunning?: boolean;
  onRerun?: () => void;
};

export function ResearchStatusBanner({
  status,
  competitorName,
  rerunning = false,
  onRerun,
}: Props) {
  if (status === "success") return null;

  if (status === "failed") {
    return (
      <div
        className={`${styles.researchBanner} ${styles.researchBannerFailed}`}
        role="status"
      >
        <div className={styles.researchBannerCopy}>
          <strong>Agent run failed</strong>
          <p>
            Research for {competitorName} did not finish successfully. Profile
            data may be incomplete. You can queue another agent run.
          </p>
        </div>
        {onRerun ? (
          <Button variant="secondary" onClick={onRerun} disabled={rerunning}>
            {rerunning ? "Rerunning…" : "Rerun agent"}
          </Button>
        ) : null}
      </div>
    );
  }

  const inProgress = status === "running" || status === "pending";
  if (!inProgress) return null;

  return (
    <div
      className={`${styles.researchBanner} ${styles.researchBannerProgress}`}
      role="status"
    >
      <div className={styles.researchBannerCopy}>
        <strong>
          {status === "running"
            ? "Agent run in progress"
            : "Agent research queued"}
        </strong>
        <p>
          We&apos;re collecting signals across the competitor&apos;s data
          sources. This status bar will clear once the run succeeds and the
          profile is populated.
        </p>
      </div>
      <span className={styles.researchBannerPulse} aria-hidden="true" />
    </div>
  );
}
