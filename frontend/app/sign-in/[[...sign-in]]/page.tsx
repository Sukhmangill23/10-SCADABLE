import { SignIn } from "@clerk/nextjs";
import { DevDashboardBypass } from "@/components/auth/DevDashboardBypass";
import { isClerkConfigured } from "@/lib/auth/config";
import styles from "../../auth.module.css";

export default function SignInPage() {
  const clerkEnabled = isClerkConfigured();

  return (
    <div className={styles.authPage}>
      <DevDashboardBypass />
      <div className={styles.copy}>
        <p className={styles.eyebrow}>Live SWOT</p>
        <h1>Welcome back</h1>
        <p className={styles.sub}>
          {clerkEnabled
            ? "Sign in to view competitors, SWOT, and agent runs."
            : "Clerk keys are not configured. Use “Go to dashboard” (top right) to explore without signing in."}
        </p>
      </div>
      {clerkEnabled ? (
        <SignIn forceRedirectUrl="/competitors" signUpUrl="/sign-up" />
      ) : (
        <div className={styles.fallbackCard}>
          <p>
            No <code>.env.local</code> Clerk keys found. Auth is skipped for local
            UI testing.
          </p>
        </div>
      )}
    </div>
  );
}
