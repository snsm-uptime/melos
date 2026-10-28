import { afterEach, describe, expect, it, vi } from "vitest";

import { clearLanguagePick, readLanguagePick, writeLanguagePick } from "@/lib/i18n/languagePick";

import { attemptSignup, saveLanguagePick } from "./signupClient";
import { signupMessages } from "@/lib/i18n/signup";
import { resolveAuthenticatedLanding } from "@/lib/landing";
import { acceptInvite, fetchInvitePreview } from "@/app/invites/inviteClient";
import { inviteMessages } from "@/lib/i18n/invite";

describe("attemptSignup", () => {
  it("returns ok on 201", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          user_id: "u1",
          email: "member@example.com",
          kitchen_id: "l1",
          kitchen_name: "Personal",
        }),
        { status: 201 },
      ),
    );
    const result = await attemptSignup({
      email: "member@example.com",
      password: "password1",
      errorDuplicate: signupMessages.en.errorDuplicate,
      errorInvalid: signupMessages.en.errorInvalid,
      errorGeneric: signupMessages.en.errorGeneric,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    expect(result).toEqual({ ok: true, invitingKitchenId: null });
  });

  it("sends invite_token and returns invitingKitchenId", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          user_id: "u1",
          email: "invitee@example.com",
          kitchen_id: "personal",
          kitchen_name: "Personal",
          inviting_kitchen_id: "invite-kitchen",
        }),
        { status: 201 },
      ),
    );
    const result = await attemptSignup({
      email: "invitee@example.com",
      password: "password1",
      inviteToken: "raw-token",
      errorDuplicate: signupMessages.en.errorDuplicate,
      errorInvalid: signupMessages.en.errorInvalid,
      errorGeneric: signupMessages.en.errorGeneric,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    expect(result).toEqual({ ok: true, invitingKitchenId: "invite-kitchen" });
    expect(fetchImpl).toHaveBeenCalledWith(
      "/api/auth/register",
      expect.objectContaining({
        body: JSON.stringify({
          email: "invitee@example.com",
          password: "password1",
          invite_token: "raw-token",
        }),
      }),
    );
  });

  it("maps email_not_verified to needsVerify for invite retain flow", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "email_not_verified" }), { status: 403 }),
    );
    const result = await attemptSignup({
      email: "invitee@example.com",
      password: "password1",
      inviteToken: "raw-token",
      errorDuplicate: signupMessages.en.errorDuplicate,
      errorInvalid: signupMessages.en.errorInvalid,
      errorGeneric: signupMessages.en.errorGeneric,
      errorNotVerified: signupMessages.en.errorNotVerified,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    expect(result).toEqual({
      ok: false,
      error: signupMessages.en.errorNotVerified,
      code: "email_not_verified",
      needsVerify: true,
    });
  });

  it("maps duplicate_email to i18n duplicate error", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "duplicate_email" }), { status: 409 }),
    );
    const result = await attemptSignup({
      email: "member@example.com",
      password: "password1",
      errorDuplicate: signupMessages.en.errorDuplicate,
      errorInvalid: signupMessages.en.errorInvalid,
      errorGeneric: signupMessages.en.errorGeneric,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    expect(result).toEqual({
      ok: false,
      error: signupMessages.en.errorDuplicate,
    });
  });

  it("returns generic error when upstream fetch throws", async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new Error("network down"));
    const result = await attemptSignup({
      email: "member@example.com",
      password: "password1",
      errorDuplicate: signupMessages.en.errorDuplicate,
      errorInvalid: signupMessages.en.errorInvalid,
      errorGeneric: signupMessages.en.errorGeneric,
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    expect(result).toEqual({
      ok: false,
      error: signupMessages.en.errorGeneric,
    });
  });
});

describe("invite landing", () => {
  it("post-invite-signup redirect targets kitchen detail not homepage", () => {
    expect(
      resolveAuthenticatedLanding({ inviteKitchenId: "invite-kitchen" }),
    ).toBe("/kitchens/invite-kitchen");
    expect(resolveAuthenticatedLanding()).toBe("/home");
  });

  it("maps expired preview to calm error", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "invalid_invite_token" }), { status: 410 }),
    );
    const result = await fetchInvitePreview(
      "bad",
      {
        errorExpired: inviteMessages.en.errorExpired,
        errorGeneric: inviteMessages.en.errorGeneric,
      },
      fetchImpl as unknown as typeof fetch,
    );
    expect(result).toEqual({
      ok: false,
      code: "invalid_invite_token",
      error: inviteMessages.en.errorExpired,
    });
  });

  it("accept returns kitchen id on success", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ kitchen_id: "kitchen-1" }), { status: 200 }),
    );
    const result = await acceptInvite(
      "tok",
      {
        errorExpired: inviteMessages.en.errorExpired,
        errorMismatch: inviteMessages.en.errorMismatch,
        errorNotVerified: inviteMessages.en.errorNotVerified,
        errorGeneric: inviteMessages.en.errorGeneric,
        errorUnauthorized: inviteMessages.en.errorUnauthorized,
      },
      fetchImpl as unknown as typeof fetch,
    );
    expect(result).toEqual({ ok: true, kitchenId: "kitchen-1" });
  });
});

describe("attemptSignup messages in the screen's language (spec 063)", () => {
  const base = {
    email: "member@example.com",
    password: "password1",
    errorDuplicate: signupMessages.es.errorDuplicate,
    errorInvalid: signupMessages.es.errorInvalid,
    errorGeneric: signupMessages.es.errorGeneric,
    errorRateLimited: signupMessages.es.errorRateLimited,
  };

  it("shows the screen's own rate-limit message, never the api's English text", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "rate_limited", detail: "Too many attempts. Please try again later." }), { status: 429 }),
    );
    const result = await attemptSignup({ ...base, fetchImpl: fetchImpl as unknown as typeof fetch });
    expect(result).toEqual({ ok: false, error: signupMessages.es.errorRateLimited });
  });

  it("shows the api's explanation in English only, and the generic message in Spanish", async () => {
    const refuse = () =>
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ code: "invalid_signup", detail: "Password must be at least 8 characters." }), { status: 400 }),
      ) as unknown as typeof fetch;
    const english = await attemptSignup({ ...base, preferServerDetail: true, fetchImpl: refuse() });
    expect(english).toEqual({ ok: false, error: "Password must be at least 8 characters." });
    const spanish = await attemptSignup({ ...base, preferServerDetail: false, fetchImpl: refuse() });
    expect(spanish).toEqual({ ok: false, error: signupMessages.es.errorInvalid });
  });
});

describe("saveLanguagePick (spec 063 FR-018)", () => {
  afterEach(() => clearLanguagePick());

  it("saves the picked language to the new account once, then drops the pick", async () => {
    // This file runs in node, so the helper gets a small cookie jar.
    const jar = new Map<string, string>();
    vi.stubGlobal("document", {
      get cookie() {
        return [...jar].map(([k, v]) => `${k}=${v}`).join("; ");
      },
      set cookie(value: string) {
        const [pair, ...attrs] = value.split(";").map((part) => part.trim());
        const [k, v] = pair.split("=");
        if (attrs.some((attr) => attr.toLowerCase() === "max-age=0")) jar.delete(k);
        else jar.set(k, v);
      },
    });
    writeLanguagePick("en");
    const fetchImpl = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));

    await saveLanguagePick(fetchImpl as unknown as typeof fetch);

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/auth/me");
    expect(init.method).toBe("PATCH");
    expect(init.body).toBe(JSON.stringify({ language: "en" }));
    expect(readLanguagePick()).toBeNull();
    vi.unstubAllGlobals();
  });

  it("sends nothing when no language was picked", async () => {
    vi.stubGlobal("document", { cookie: "" });
    const fetchImpl = vi.fn();
    await saveLanguagePick(fetchImpl as unknown as typeof fetch);
    expect(fetchImpl).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("does not throw when the save fails, and still drops the pick", async () => {
    const jar = new Map<string, string>([["melos_lang", "en"]]);
    vi.stubGlobal("document", {
      get cookie() {
        return [...jar].map(([k, v]) => `${k}=${v}`).join("; ");
      },
      set cookie(value: string) {
        const [pair, ...attrs] = value.split(";").map((part) => part.trim());
        const [k, v] = pair.split("=");
        if (attrs.some((attr) => attr.toLowerCase() === "max-age=0")) jar.delete(k);
        else jar.set(k, v);
      },
    });
    const fetchImpl = vi.fn().mockRejectedValue(new Error("down"));
    await expect(saveLanguagePick(fetchImpl as unknown as typeof fetch)).resolves.toBeUndefined();
    expect(jar.has("melos_lang")).toBe(false);
    vi.unstubAllGlobals();
  });
});
