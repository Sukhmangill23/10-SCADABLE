/**
 * True when Clerk publishable key is present (usually via .env.local).
 * Never read .env files directly — only process.env values Next injects.
 */
export function isClerkConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.trim());
}
