/**
 * First-paint / post-auth landing choke (UX-DR9).
 * Story 2.4 passes inviteKitchenId to land on the inviting kitchen instead of the default one.
 */
export type AuthenticatedLandingInput = {
  inviteKitchenId?: string | null;
};

export function resolveAuthenticatedLanding(
  input: AuthenticatedLandingInput = {},
): string {
  const invite = input.inviteKitchenId?.trim();
  if (invite) {
    return `/kitchens/${encodeURIComponent(invite)}`;
  }
  return "/home";
}
