"use client";

import { ClerkProvider } from "@clerk/nextjs";
import type { ReactNode } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { QueryProvider } from "@/lib/providers/QueryProvider";

type Props = {
  children: ReactNode;
  clerkEnabled: boolean;
};

export function AppProviders({ children, clerkEnabled }: Props) {
  const body = (
    <QueryProvider>
      <AppShell clerkEnabled={clerkEnabled}>{children}</AppShell>
    </QueryProvider>
  );

  if (!clerkEnabled) {
    return body;
  }

  return (
    <ClerkProvider
      signInFallbackRedirectUrl="/overview"
      signUpFallbackRedirectUrl="/overview"
      afterSignOutUrl="/sign-in"
    >
      {body}
    </ClerkProvider>
  );
}
