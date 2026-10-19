/**
 * First-paint / post-auth landing choke (UX-DR9).
 * Story 2.4 passes inviteKitchenId to land on the inviting kitchen instead of remember-last.
 */
export type AuthenticatedLandingInput = {
  inviteKitchenId?: string | null;
  lastOpenedKitchenId?: string | null;
  lastOpenedStillAccessible?: boolean;
};

export function resolveAuthenticatedLanding(
  input: AuthenticatedLandingInput = {},
): string {
  const invite = input.inviteKitchenId?.trim();
  if (invite) {
    return `/kitchens/${encodeURIComponent(invite)}`;
  }
  const remembered = input.lastOpenedKitchenId?.trim();
  if (remembered && input.lastOpenedStillAccessible) {
    return `/kitchens/${encodeURIComponent(remembered)}`;
  }
  return "/home";
}
