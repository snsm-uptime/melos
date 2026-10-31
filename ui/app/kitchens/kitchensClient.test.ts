import { describe, expect, it, vi, afterEach } from "vitest";

import {
  archiveKitchen,
  createKitchen,
  fetchKitchens,
  inviteMember,
  renameKitchen,
  unarchiveKitchen,
} from "./kitchensClient";
import {
  getMembershipKitchensSnapshot,
  replaceMembershipKitchens,
  resetMembershipKitchensStore,
} from "./membershipKitchensStore";

const messages = {
  errorGeneric: "generic",
  errorInvalidName: "invalid",
  errorForbidden: "forbidden",
  errorUnauthorized: "unauthorized",
  errorInvalidEmail: "bad-email",
  errorAlreadyMember: "already",
  errorSmtp: "smtp",
};

afterEach(() => {
  vi.unstubAllGlobals();
  resetMembershipKitchensStore();
});

describe("kitchensClient", () => {
  it("maps 403 on rename to forbidden message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({ code: "not_kitchen_owner", detail: "nope" }),
      }),
    );

    const result = await renameKitchen("kitchen-1", "New", messages);
    expect(result).toEqual({ ok: false, error: "forbidden" });
  });

  it("fetchKitchens returns membership kitchens on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        kitchens: [{ id: "l1", name: "Household", owner_id: "u1", role: "owner" }],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchKitchens(messages);
    expect(result).toEqual({
      ok: true,
      kitchens: [{ id: "l1", name: "Household", owner_id: "u1", role: "owner" }],
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/kitchens", expect.objectContaining({ method: "GET" }));
  });

  it("fetchKitchens maps a failure response to the generic message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({ detail: "Not authenticated." }),
      }),
    );

    const result = await fetchKitchens(messages);
    expect(result).toEqual({ ok: false, error: "unauthorized" });
  });

  it("returns created kitchen on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => ({
          id: "a",
          name: "Household",
          owner_id: "u1",
        }),
      }),
    );

    const result = await createKitchen("Household", messages);
    expect(result).toEqual({
      ok: true,
      kitchen: { id: "a", name: "Household", owner_id: "u1" },
    });
  });

  it("returns generic error when success body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 201,
        json: async () => {
          throw new Error("bad json");
        },
      }),
    );

    const result = await createKitchen("Household", messages);
    expect(result).toEqual({ ok: false, error: "generic" });
  });

  it("inviteMember returns sent state on success", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 201,
      json: async () => ({
        status: "sent",
        template_kind: "signup",
        invite_id: "inv-1",
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await inviteMember("kitchen-1", "new@example.com", messages);
    expect(result).toEqual({
      ok: true,
      invite: {
        status: "sent",
        template_kind: "signup",
        invite_id: "inv-1",
      },
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/kitchens/kitchen-1/invites",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("inviteMember maps SMTP failure without claiming sent", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ code: "smtp_send_error", detail: "down" }),
      }),
    );

    const result = await inviteMember("kitchen-1", "new@example.com", messages);
    expect(result).toEqual({ ok: false, error: "smtp" });
  });

  it("inviteMember maps already-member conflict", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ code: "already_kitchen_member" }),
      }),
    );

    const result = await inviteMember("kitchen-1", "member@example.com", messages);
    expect(result).toEqual({ ok: false, error: "already" });
  });
});

describe("kitchensClient archive (Story 9.2)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    resetMembershipKitchensStore();
  });

  it("fetchKitchens({ archived: true }) hits the archived query param and does not replace the membership store", async () => {
    replaceMembershipKitchens([{ id: "l1", name: "Household", owner_id: "u1", role: "owner" }]);
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        kitchens: [{ id: "l2", name: "Archived kitchen", owner_id: "u1", role: "owner", is_archived: true }],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await fetchKitchens(messages, { archived: true });
    expect(result.ok).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/kitchens?archived=true",
      expect.objectContaining({ method: "GET" }),
    );
    // Store must still hold the non-archived snapshot seeded above.
    expect(getMembershipKitchensSnapshot()).toEqual([
      { id: "l1", name: "Household", owner_id: "u1", role: "owner" },
    ]);
  });

  it("fetchKitchens() without options still hits plain /api/kitchens and replaces the store", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        kitchens: [{ id: "l1", name: "Household", owner_id: "u1", role: "owner" }],
      }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await fetchKitchens(messages);
    expect(fetchMock).toHaveBeenCalledWith("/api/kitchens", expect.objectContaining({ method: "GET" }));
    expect(getMembershipKitchensSnapshot()).toEqual([
      { id: "l1", name: "Household", owner_id: "u1", role: "owner" },
    ]);
  });

  it("archiveKitchen posts to /api/kitchens/{id}/archive and removes the kitchen from the membership store", async () => {
    replaceMembershipKitchens([
      { id: "l1", name: "Household", owner_id: "u1", role: "owner" },
      { id: "l2", name: "Other", owner_id: "u1", role: "owner" },
    ]);
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "l1", name: "Household", owner_id: "u1", is_archived: true }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await archiveKitchen("l1", messages);
    expect(result).toEqual({
      ok: true,
      kitchen: { id: "l1", name: "Household", owner_id: "u1", is_archived: true },
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/kitchens/l1/archive",
      expect.objectContaining({ method: "POST" }),
    );
    expect(getMembershipKitchensSnapshot()).toEqual([
      { id: "l2", name: "Other", owner_id: "u1", role: "owner" },
    ]);
  });

  it("archiveKitchen maps a 403 (non-owner) response to the forbidden message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({ code: "not_kitchen_owner", detail: "nope" }),
      }),
    );

    const result = await archiveKitchen("l1", messages);
    expect(result).toEqual({ ok: false, error: "forbidden" });
  });

  it("unarchiveKitchen posts to /api/kitchens/{id}/unarchive", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ id: "l1", name: "Household", owner_id: "u1", is_archived: false }),
    });
    vi.stubGlobal("fetch", fetchMock);

    const result = await unarchiveKitchen("l1", messages);
    expect(result).toEqual({
      ok: true,
      kitchen: { id: "l1", name: "Household", owner_id: "u1", is_archived: false },
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/kitchens/l1/unarchive",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("unarchiveKitchen maps a 403 response to the forbidden message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        json: async () => ({ code: "not_kitchen_owner", detail: "nope" }),
      }),
    );

    const result = await unarchiveKitchen("l1", messages);
    expect(result).toEqual({ ok: false, error: "forbidden" });
  });
});

describe("unarchiveKitchen and the panel's list (spec 064 FR-017)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    resetMembershipKitchensStore();
  });

  const restored = { id: "k9", name: "Old", owner_id: "u1", is_archived: false };

  it("adds the restored kitchen to the membership store", async () => {
    replaceMembershipKitchens([]);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(restored))));
    await unarchiveKitchen("k9", messages);
    expect(getMembershipKitchensSnapshot()?.map((k) => k.id)).toEqual(["k9"]);
  });

  it("changes nothing when the restore fails", async () => {
    replaceMembershipKitchens([]);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 403 })));
    await unarchiveKitchen("k9", messages);
    expect(getMembershipKitchensSnapshot()).toEqual([]);
  });
});
