/**
 * Clerk invitation acceptance links include a ticket query param.
 * Without it, /sign-up should not be shown (restricted mode shows "Access restricted").
 */
export function hasClerkInviteTicket(searchParams: URLSearchParams): boolean {
  return (
    searchParams.has("__clerk_ticket") ||
    searchParams.has("__clerk_invitation_token") ||
    searchParams.has("ticket")
  );
}
