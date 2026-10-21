import type { ReactNode } from "react";
import styles from "./Pill.module.css";

export function Pill({ children }: { children: ReactNode }) {
  return <span className={styles.pill}>{children}</span>;
}
