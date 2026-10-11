import { SignUp } from "@clerk/nextjs";
import { DevDashboardBypass } from "@/components/auth/DevDashboardBypass";
import { isClerkConfigured } from "@/lib/auth/config";
import styles from "../../auth.module.css";

export default function SignUpPage() {
  const clerkEnabled = isClerkConfigured();

  return (
    <div className={styles.authPage}>
      <DevDashboardBypass />
      <div className={styles.copy}>
        <p className={styles.eyebrow}>Live SWOT</p>
        <h1>Create your account</h1>
        <p className={styles.sub}>
          {clerkEnabled
            ? "Internal competitor intelligence for SCADABLE. Sign up to get started."
            : "Clerk keys are not configured in this checkout. Use “Go to dashboard” (top right) to explore the UI without signing in."}
        </p>
      </div>
      {clerkEnabled ? (
        <SignUp forceRedirectUrl="/competitors" signInUrl="/sign-in" />
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
