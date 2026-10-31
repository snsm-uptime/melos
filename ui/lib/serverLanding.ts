import { resolveAuthenticatedLanding } from "@/lib/landing";

/** First-paint path: an invite's kitchen, else `/home`, which opens the default kitchen. */
export async function resolveServerAuthenticatedLanding(options?: {
  inviteKitchenId?: string | null;
}): Promise<string> {
  return resolveAuthenticatedLanding({ inviteKitchenId: options?.inviteKitchenId });
}
