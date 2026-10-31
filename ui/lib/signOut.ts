import { resetMembershipKitchensStore } from "@/app/kitchens/membershipKitchensStore";
import { clearPrefsCache } from "@/components/PreferencesProvider";

/** End the session, clear cached personal data, and open `target` even if the network fails. */
export async function signOut(target: string): Promise<void> {
  clearPrefsCache();
  resetMembershipKitchensStore();
  try {
    await fetch("/api/auth/sign-out", {
      method: "POST",
      credentials: "same-origin",
      cache: "no-store",
    });
  } finally {
    clearPrefsCache();
    resetMembershipKitchensStore();
    window.location.assign(target);
  }
}
