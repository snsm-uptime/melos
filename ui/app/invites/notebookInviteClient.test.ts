import { afterEach, describe, expect, it, vi } from "vitest";

import { acceptNotebookInvite, fetchNotebookInvitePreview } from "./notebookInviteClient";

function reply(status: number, body: unknown) {
  return vi.fn(async () => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  })) as unknown as typeof fetch;
}

afterEach(() => vi.unstubAllGlobals());

describe("fetchNotebookInvitePreview", () => {
  it("returns the safe fields and allows a missing sender", async () => {
    const preview = { notebook_name: "Recetas", inviter_alias: null, email_hint: "b***n@x.test" };
    expect(await fetchNotebookInvitePreview("t", reply(200, preview))).toEqual({
      ok: true,
      preview,
    });
  });

  it("calls the BFF with an encoded token", async () => {
    const impl = reply(410, { code: "invalid_invite_token" });
    await fetchNotebookInvitePreview("a b", impl);
    expect((impl as unknown as { mock: { calls: string[][] } }).mock.calls[0][0]).toBe(
      "/api/invites/notebook/preview?token=a%20b",
    );
  });

  it("maps a dead link to invalid", async () => {
    expect(await fetchNotebookInvitePreview("t", reply(410, {}))).toEqual({
      ok: false,
      code: "invalid_invite_token",
    });
  });

  it("treats a malformed body as an error", async () => {
    expect(await fetchNotebookInvitePreview("t", reply(200, { notebook_name: 1 }))).toEqual({
      ok: false,
      code: "error",
    });
  });
});

describe("acceptNotebookInvite", () => {
  it("returns the notebook id", async () => {
    expect(await acceptNotebookInvite("t", reply(200, { notebook_id: "n1" }))).toEqual({
      ok: true,
      notebookId: "n1",
    });
  });

  it.each([
    [401, {}, "unauthorized"],
    [403, { code: "alias_required" }, "alias_required"],
    [403, { code: "email_not_verified" }, "email_not_verified"],
    [403, { code: "invite_email_mismatch" }, "invite_email_mismatch"],
    [410, { code: "invalid_invite_token" }, "invalid_invite_token"],
    [500, {}, "error"],
  ])("maps %i %j to %s", async (status, body, code) => {
    expect(await acceptNotebookInvite("t", reply(status, body))).toEqual({ ok: false, code });
  });

  it("maps a network failure to an error", async () => {
    const impl = vi.fn(async () => {
      throw new Error("down");
    }) as unknown as typeof fetch;
    expect(await acceptNotebookInvite("t", impl)).toEqual({ ok: false, code: "error" });
  });
});
