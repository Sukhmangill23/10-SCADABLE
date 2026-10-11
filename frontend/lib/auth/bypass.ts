export const DEV_DASHBOARD_BYPASS_COOKIE = "live_swot_dev_dashboard";

/** Bypass is for local/team testing. Never treat this as real auth. */
export function isDevDashboardBypassAllowed(): boolean {
  return (
    process.env.NODE_ENV === "development" ||
    process.env.ALLOW_DEV_DASHBOARD_BYPASS === "true"
  );
}
