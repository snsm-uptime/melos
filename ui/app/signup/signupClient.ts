import { clearLanguagePick, readLanguagePick } from "@/lib/i18n/languagePick";

/** Pure helpers for signup form (unit-tested without a React render). */

export type SignupAttemptResult =
  | { ok: true; invitingKitchenId?: string | null }
  | {
      ok: false;
      error: string;
      code?: string;
      needsVerify?: boolean;
    };

export async function attemptSignup(args: {
  email: string;
  password: string;
  inviteToken?: string | null;
  errorDuplicate: string;
  errorInvalid: string;
  errorGeneric: string;
  /** Shown for a 429; the api's own text is English and is never shown. */
  errorRateLimited?: string;
  /** Show the api's message for a refused sign-up (English only); otherwise the generic one. */
  preferServerDetail?: boolean;
  errorExpiredInvite?: string;
  errorInviteMismatch?: string;
  errorNotVerified?: string;
  fetchImpl?: typeof fetch;
}): Promise<SignupAttemptResult> {
  const fetchFn = args.fetchImpl ?? fetch;
  const body: Record<string, string> = {
    email: args.email,
    password: args.password,
  };
  if (args.inviteToken) {
    body.invite_token = args.inviteToken;
  }
  try {
    const response = await fetchFn("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
      credentials: "same-origin",
    });
    const data = (await response.json().catch(() => ({}))) as {
      detail?: string;
      code?: string;
      inviting_kitchen_id?: string | null;
    };
    if (!response.ok) {
      if (data.code === "email_not_verified" || response.status === 403) {
        if (data.code === "email_not_verified") {
          return {
            ok: false,
            error: args.errorNotVerified || args.errorGeneric,
            code: "email_not_verified",
            needsVerify: true,
          };
        }
        if (data.code === "invite_email_mismatch") {
          return {
            ok: false,
            error: args.errorInviteMismatch || args.errorGeneric,
            code: "invite_email_mismatch",
          };
        }
      }
      if (data.code === "invalid_invite_token" || response.status === 410) {
        return {
          ok: false,
          error: args.errorExpiredInvite || args.errorGeneric,
          code: "invalid_invite_token",
        };
      }
      if (data.code === "rate_limited" || response.status === 429) {
        return {
          ok: false,
          error: args.errorRateLimited || args.errorGeneric,
        };
      }
      if (data.code === "duplicate_email") {
        return { ok: false, error: args.errorDuplicate };
      }
      if (data.code === "invalid_signup" || response.status === 400) {
        return {
          ok: false,
          error: (args.preferServerDetail !== false && data.detail) || args.errorInvalid,
        };
      }
      return { ok: false, error: args.errorGeneric };
    }
    return {
      ok: true,
      invitingKitchenId:
        typeof data.inviting_kitchen_id === "string" ? data.inviting_kitchen_id : null,
    };
  } catch {
    return { ok: false, error: args.errorGeneric };
  }
}

/**
 * Save the language the visitor picked on the signed-out screens to the new account (spec 063
 * FR-018), then drop the pick. With no pick the account keeps no saved language, which is
 * Spanish. A failed save is ignored: the account then has no saved language.
 */
export async function saveLanguagePick(fetchImpl: typeof fetch = fetch): Promise<void> {
  const pick = readLanguagePick();
  if (!pick) return;
  try {
    await fetchImpl("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ language: pick }),
      credentials: "same-origin",
    });
  } catch {
    /* the account keeps no saved language */
  } finally {
    clearLanguagePick();
  }
}
