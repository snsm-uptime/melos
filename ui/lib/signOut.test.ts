/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const clearPrefsCache = vi.fn();
const resetMembershipKitchensStore = vi.fn();
vi.mock("@/components/PreferencesProvider", () => ({
  clearPrefsCache: () => clearPrefsCache(),
}));
vi.mock("@/app/kitchens/membershipKitchensStore", () => ({
  resetMembershipKitchensStore: () => resetMembershipKitchensStore(),
}));

import { getCaptureState, setText } from "./capture/captureStore";
import { signOut } from "./signOut";

describe("signOut", () => {
  const assign = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("location", { assign });
  });
  afterEach(() => vi.unstubAllGlobals());

  it("clears before and after the request, then opens the target", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);
    await signOut("/sign-in");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/sign-out");
    expect(clearPrefsCache).toHaveBeenCalledTimes(2);
    expect(resetMembershipKitchensStore).toHaveBeenCalledTimes(2);
    expect(assign).toHaveBeenCalledWith("/sign-in");
  });

  it("clears the kept capture text (spec 076 FR-004)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    setText("abc");
    expect(window.sessionStorage.getItem("melos.capture.text")).toBe("abc");
    await signOut("/");
    expect(window.sessionStorage.getItem("melos.capture.text")).toBeNull();
    expect(getCaptureState().text).toBe("");
  });

  it("still opens the target when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
    await expect(signOut("/forgot-password")).rejects.toThrow("offline");
    expect(assign).toHaveBeenCalledWith("/forgot-password");
  });
});
