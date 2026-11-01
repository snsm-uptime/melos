/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AcceptNotebookInvitePanel } from "./AcceptNotebookInvitePanel";

const replace = vi.fn();
const refresh = vi.fn();
const router = { replace, refresh };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

const accept = vi.fn();
const preview = vi.fn();
vi.mock("../notebookInviteClient", () => ({
  acceptNotebookInvite: (...args: unknown[]) => accept(...args),
  fetchNotebookInvitePreview: (...args: unknown[]) => preview(...args),
}));

describe("AcceptNotebookInvitePanel", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    replace.mockReset();
    refresh.mockReset();
    accept.mockReset();
    preview.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  async function render(authenticated: boolean, token = "tok", locale: "en" | "es" = "en") {
    await act(async () => {
      root.render(
        <AcceptNotebookInvitePanel locale={locale} token={token} authenticated={authenticated} />,
      );
    });
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }

  const hrefs = () =>
    Array.from(container.querySelectorAll("a")).map((a) => a.getAttribute("href"));

  it("joins on open with no button and lands on the notebook", async () => {
    accept.mockResolvedValue({ ok: true, notebookId: "n1" });
    await render(true);
    expect(accept).toHaveBeenCalledTimes(1);
    expect(replace).toHaveBeenCalledWith("/notebooks/n1");
    expect(container.querySelector("button")).toBeNull();
    expect(preview).not.toHaveBeenCalled();
  });

  it("sends a person with no alias to set one, then back to the link", async () => {
    accept.mockResolvedValue({ ok: false, code: "alias_required" });
    await render(true, "a b");
    expect(replace).toHaveBeenCalledWith(
      `/alias?returnTo=${encodeURIComponent("/invites/notebook?token=a%20b")}`,
    );
  });

  it("asks an unverified person to verify and return", async () => {
    accept.mockResolvedValue({ ok: false, code: "email_not_verified" });
    await render(true);
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Verify");
    expect(hrefs()).toEqual([
      `/verify?returnTo=${encodeURIComponent("/invites/notebook?token=tok")}`,
    ]);
  });

  it("says when the invite is for another email", async () => {
    accept.mockResolvedValue({ ok: false, code: "invite_email_mismatch" });
    await render(true);
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("another email");
    expect(replace).not.toHaveBeenCalled();
  });

  it("shows one message for a dead link, in Spanish with cuaderno", async () => {
    accept.mockResolvedValue({ ok: false, code: "invalid_invite_token" });
    await render(true, "tok", "es");
    const text = container.querySelector('[role="alert"]')?.textContent ?? "";
    expect(text).toContain("cuaderno");
    expect(text).not.toContain("lista");
  });

  it("shows a missing token as a dead link without calling anything", async () => {
    await render(true, "");
    expect(accept).not.toHaveBeenCalled();
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
  });

  it("signed out, shows the name, alias, masked email, both ways in and the reopen note", async () => {
    preview.mockResolvedValue({
      ok: true,
      preview: {
        notebook_name: "Recetas",
        inviter_alias: "ana",
        email_hint: "b***n@example.test",
      },
    });
    await render(false);
    expect(accept).not.toHaveBeenCalled();
    const text = container.textContent ?? "";
    expect(text).toContain("Recetas");
    expect(text).toContain("ana");
    expect(text).toContain("b***n@example.test");
    expect(text).toContain("open this link again");
    expect(hrefs()).toEqual([
      `/sign-in?returnTo=${encodeURIComponent("/invites/notebook?token=tok")}`,
      "/signup",
    ]);
  });

  it("signed out, leaves out the inviter when the sender is gone", async () => {
    preview.mockResolvedValue({
      ok: true,
      preview: { notebook_name: "Recetas", inviter_alias: null, email_hint: "b***n@x.test" },
    });
    await render(false);
    expect(container.textContent).toContain("Recetas");
    expect(container.textContent).not.toContain("null");
  });

  it("signed out with a dead link reveals nothing and offers no way in", async () => {
    preview.mockResolvedValue({ ok: false, code: "invalid_invite_token" });
    await render(false);
    expect(container.querySelector('[role="alert"]')).not.toBeNull();
    expect(hrefs()).toEqual([]);
  });
});
