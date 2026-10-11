"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import styles from "./AppShell.module.css";

const NAV = [
  { href: "/overview", label: "Overview", short: "O" },
  { href: "/competitors", label: "Competitors", short: "C" },
  { href: "/company", label: "Our Company", short: "S" },
  { href: "/runs", label: "Agent Runs", short: "R" },
  { href: "/sign-in", label: "Sign in", short: "A" },
] as const;

function titleForPath(pathname: string): string {
  if (pathname.startsWith("/competitors/")) return "Competitor profile";
  if (pathname.startsWith("/runs/")) return "Agent run";
  const match = NAV.find((item) => item.href === pathname);
  return match?.label ?? "Live SWOT";
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.brandMark} aria-hidden="true">
          LS
        </div>
        <div className={styles.title}>{titleForPath(pathname)}</div>
      </header>

      <nav className={styles.sidebar} aria-label="Primary">
        {NAV.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`${styles.navItem} ${active ? styles.navItemActive : ""}`}
              aria-label={item.label}
              aria-current={active ? "page" : undefined}
            >
              {item.short}
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <main className={styles.main}>{children}</main>
    </div>
  );
}
