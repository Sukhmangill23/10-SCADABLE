import Link from "next/link";
import styles from "./DevDashboardBypass.module.css";

/**
 * Always shown. Hits an API route that sets a bypass cookie, then opens the app.
 * Works with or without Clerk keys configured.
 */
export function DevDashboardBypass() {
  return (
    <div className={styles.bar}>
      <p className={styles.note}>Dev only</p>
      <Link href="/api/dev/dashboard-bypass" className={styles.button}>
        Go to dashboard
      </Link>
    </div>
  );
}
