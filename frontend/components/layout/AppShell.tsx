"use client";

import {
  Show,
  SignInButton,
  UserButton,
} from "@clerk/nextjs";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import styles from "./AppShell.module.css";

const NAV = [
  { href: "/overview", label: "Overview", short: "O" },
  { href: "/competitors", label: "Competitors", short: "C" },
  { href: "/company", label: "Our Company", short: "S" },
  { href: "/runs", label: "Agent Runs", short: "R" },
] as const;

function titleForPath(pathname: string): string {
  if (pathname.startsWith("/competitors/")) return "Competitor profile";
  if (pathname.startsWith("/runs/")) return "Agent run";
  if (pathname.startsWith("/sign-up")) return "Accept invite";
  if (pathname.startsWith("/sign-in")) return "Sign in";
  const match = NAV.find((item) => item.href === pathname);
  return match?.label ?? "Live SWOT";
}

function isAuthRoute(pathname: string) {
  return pathname.startsWith("/sign-in") || pathname.startsWith("/sign-up");
}

type Props = {
  children: ReactNode;
  clerkEnabled: boolean;
};

export function AppShell({ children, clerkEnabled }: Props) {
  const pathname = usePathname();

  if (isAuthRoute(pathname)) {
    return <>{children}</>;
  }

  return (
    <div className={styles.shell}>
      <header className={styles.topbar}>
        <div className={styles.brandMark} aria-hidden="true">
          LS
        </div>
        <div className={styles.titleRow}>
          <div className={styles.title}>{titleForPath(pathname)}</div>
          <div className={styles.authControls}>
            {!clerkEnabled ? (
              <span className={styles.devBadge}>Auth bypass (no Clerk keys)</span>
            ) : (
              <>
                <Show when="signed-out">
                  <SignInButton mode="redirect">
                    <button type="button" className={styles.authBtnPrimary}>
                      Sign in
                    </button>
                  </SignInButton>
                </Show>
                <Show when="signed-in">
                  <UserButton />
                </Show>
              </>
            )}
          </div>
        </div>
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
