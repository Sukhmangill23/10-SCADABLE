/** Host only for display (no https://), matching the mockup. */
export function displayWebsite(website: string): string {
  return website.replace(/^https?:\/\//, "");
}

/** Relative past time for mock / API timestamps. */
export function formatRelativePast(iso: string | null): string {
  if (!iso) return "Not checked";

  const then = new Date(iso).getTime();
  const now = Date.now();
  const days = Math.max(0, Math.floor((now - then) / (1000 * 60 * 60 * 24)));

  if (days === 0) return "Today";
  if (days === 1) return "1 day ago";
  if (days < 7) return `${days} days ago`;
  if (days < 14) return "1 week ago";
  if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
  if (days < 60) return "1 month ago";
  return `${Math.floor(days / 30)} months ago`;
}

/** Relative future time for next refresh. */
export function formatRelativeFuture(iso: string | null): string {
  if (!iso) return "Not scheduled";

  const then = new Date(iso).getTime();
  const now = Date.now();
  const days = Math.ceil((then - now) / (1000 * 60 * 60 * 24));

  if (days <= 0) return "Due now";
  if (days === 1) return "in 1 day";
  return `in ${days} days`;
}
