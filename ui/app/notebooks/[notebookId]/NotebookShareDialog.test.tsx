/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NotebookShareDialog } from "./NotebookShareDialog";

const replace = vi.fn();
const onOpenChange = vi.fn();
const router = { replace, push: vi.fn() };
vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));
const owner = { user_id: "u1", alias: "ana", role: "owner", is_self: true };
const ben = { user_id: "u2", alias: "ben", role: "member", is_self: false };
const open = { id: "i1", email: "carla@example.test", expires_at: "2026-11-08T15:00:00Z", expired: false };
const old = { id: "i2", email: "dan@example.test", expires_at: "2026-10-01T15:00:00Z", expired: true };

type Reply = { status: number; body?: unknown };
type Calls = { url: string; method: string; body?: string }[];

function stub(routes: Record<string, Reply | (() => Reply)>): Calls {
  const calls: Calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      calls.push({ url, method, body: init?.body as string | undefined });
      const route = routes[`${method} ${url}`];
      const reply = typeof route === "function" ? route() : route;
      if (!reply) throw new Error(`no route for ${method} ${url}`);
      return {
        ok: reply.status >= 200 && reply.status < 300,
        status: reply.status,
        json: async () => reply.body,
      };
    }),
  );
  return calls;
}

const BASE = "/api/notebooks/nb-1";

function ownerRoutes(invites: unknown[] = [open, old]) {
  return {
    [`GET ${BASE}/members`]: { status: 200, body: { members: [owner, ben] } },
    [`GET ${BASE}/invites`]: { status: 200, body: { invites } },
  };
}

function memberRoutes() {
  return {
    [`GET ${BASE}/members`]: {
      status: 200,
      body: {
        members: [
          { ...owner, is_self: false },
          { ...ben, is_self: true },
        ],
      },
    },
  };
}

describe("NotebookShareDialog", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    replace.mockReset();
    onOpenChange.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  async function flush() {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }

  async function render(isOwner = true) {
    await act(async () => {
      root.render(
        <NotebookShareDialog
          open
          onOpenChange={onOpenChange}
          notebookId="nb-1"
          isOwner={isOwner}
          locale="en"
        />,
      );
    });
    await flush();
    await flush();
  }

  const button = (name: string, from: ParentNode = document.body) =>
    Array.from(from.querySelectorAll("button")).find(
      (el) => el.textContent === name || el.getAttribute("aria-label") === name,
    );
  const dialog = () => document.body.querySelector('[role="dialog"]') as HTMLElement;

  async function click(el: Element | undefined) {
    expect(el).toBeTruthy();
    await act(async () => {
      el!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    });
    await flush();
    await flush();
  }

  async function typeEmail(value: string) {
    const input = container.querySelector('input[type="email"]') as HTMLInputElement;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
    return input;
  }

  async function submit() {
    const form = container.querySelector("form") as HTMLFormElement;
    await act(async () => {
      form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
    await flush();
    await flush();
  }

  it("shows the owner the members, the form and the invites, with no Leave", async () => {
    stub(ownerRoutes());
    await render();
    const text = container.textContent ?? "";
    expect(text).toContain("ana");
    expect(text).toContain("ben");
    expect(text).toContain("carla@example.test");
    expect(text).toContain("Expired");
    expect(container.querySelector('input[type="email"]')).not.toBeNull();
    expect(button("Leave this notebook")).toBeUndefined();
    expect(button("Remove ben")).toBeTruthy();
    expect(button("Remove ana")).toBeUndefined();
  });

  it("shows a member the list and Leave, with no invites, form or Remove", async () => {
    const calls = stub(memberRoutes());
    await render(false);
    expect(container.textContent).toContain("ana");
    expect(calls.some((call) => call.url.endsWith("/invites"))).toBe(false);
    expect(container.querySelector('input[type="email"]')).toBeNull();
    expect(button("Remove ana")).toBeUndefined();
    expect(button("Leave this notebook")).toBeTruthy();
  });

  it("shows unknown for a person with no alias", async () => {
    stub({
      ...ownerRoutes([]),
      [`GET ${BASE}/members`]: {
        status: 200,
        body: { members: [owner, { ...ben, alias: null }] },
      },
    });
    await render();
    expect(container.textContent).toContain("unknown");
  });

  it("sends an invite, announces it and refreshes the list", async () => {
    let invites: unknown[] = [];
    const calls = stub({
      ...ownerRoutes(),
      [`GET ${BASE}/invites`]: () => ({ status: 200, body: { invites } }),
      [`POST ${BASE}/invites`]: () => {
        invites = [open];
        return { status: 201, body: { status: "sent", invite: open } };
      },
    });
    await render();
    await typeEmail("carla@example.test");
    await submit();
    const post = calls.find((call) => call.method === "POST");
    expect(JSON.parse(post!.body!)).toEqual({ email: "carla@example.test" });
    expect(container.querySelector('[role="status"]')?.textContent).toContain("carla@example.test");
    expect(container.textContent).toContain("Expires");
  });

  it.each([
    ["already_in_notebook", 409, "already in this notebook"],
    ["invalid_invite_email", 422, "valid email"],
    ["smtp_send_error", 503, "could not be sent"],
  ])("explains %s", async (code, status, text) => {
    stub({ ...ownerRoutes(), [`POST ${BASE}/invites`]: { status, body: { code } } });
    await render();
    await typeEmail("x@example.test");
    await submit();
    expect(container.querySelector("[role='alert']")?.textContent).toContain(text);
  });

  it("confirms before leaving, then goes to the notebooks", async () => {
    const calls = stub({
      ...memberRoutes(),
      [`DELETE ${BASE}/members/me`]: { status: 204 },
    });
    await render(false);
    await click(button("Leave this notebook"));
    expect(calls.some((call) => call.method === "DELETE")).toBe(false);
    await click(button("Leave", dialog()));
    expect(calls.some((call) => call.method === "DELETE")).toBe(true);
    expect(replace).toHaveBeenCalledWith("/notebooks");
  });

  it("confirms before removing, then the person leaves the list", async () => {
    let members = [owner, ben];
    const calls = stub({
      ...ownerRoutes([]),
      [`GET ${BASE}/members`]: () => ({ status: 200, body: { members } }),
      [`DELETE ${BASE}/members/u2`]: () => {
        members = [owner];
        return { status: 204 };
      },
    });
    await render();
    await click(button("Remove ben"));
    expect(dialog().textContent).toContain("ben");
    expect(calls.some((call) => call.method === "DELETE")).toBe(false);
    await click(button("Remove", dialog()));
    expect(calls.some((call) => call.url === `${BASE}/members/u2`)).toBe(true);
    expect(button("Remove ben")).toBeUndefined();
  });

  it("resends an invite and says so", async () => {
    const calls = stub({
      ...ownerRoutes(),
      [`POST ${BASE}/invites/i2/resend`]: { status: 200, body: { status: "sent", invite: old } },
    });
    await render();
    await click(button("Resend to dan@example.test"));
    expect(calls.some((call) => call.url.endsWith("/i2/resend"))).toBe(true);
    expect(container.querySelector('[role="status"]')?.textContent).toContain("dan@example.test");
  });

  it("confirms before cancelling an invite", async () => {
    let invites = [open];
    const calls = stub({
      ...ownerRoutes(),
      [`GET ${BASE}/invites`]: () => ({ status: 200, body: { invites } }),
      [`DELETE ${BASE}/invites/i1`]: () => {
        invites = [];
        return { status: 204 };
      },
    });
    await render();
    await click(button("Cancel invite to carla@example.test"));
    expect(calls.some((call) => call.method === "DELETE")).toBe(false);
    await click(button("Cancel invite", dialog()));
    expect(calls.some((call) => call.method === "DELETE")).toBe(true);
    expect(button("Cancel invite to carla@example.test")).toBeUndefined();
    expect(container.querySelector('[role="status"]')?.textContent).toContain("was cancelled");
  });

  it("goes to the notebooks on a 404", async () => {
    stub({ [`GET ${BASE}/members`]: { status: 404, body: { code: "notebook_not_found" } } });
    await render(false);
    expect(replace).toHaveBeenCalledWith("/notebooks");
  });

  it("goes back from a confirmation without closing the dialog", async () => {
    stub(ownerRoutes());
    await render();
    await click(button("Remove ben"));
    await click(button("Go back", dialog()));
    expect(onOpenChange).not.toHaveBeenCalled();
    expect(button("Remove ben")).toBeTruthy();
  });

  it("moves focus into a confirmation, for the keyboard", async () => {
    stub(ownerRoutes());
    await render();
    await click(button("Remove ben"));
    expect(dialog().contains(document.activeElement)).toBe(true);
  });

  it("closes from the main view", async () => {
    stub(ownerRoutes());
    await render();
    await click(button("Close", dialog()));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("goes to the notebooks when an action answers 404 because access ended", async () => {
    stub({
      ...ownerRoutes(),
      [`POST ${BASE}/invites/i2/resend`]: {
        status: 404,
        body: { code: "notebook_not_found" },
      },
    });
    await render();
    await click(button("Resend to dan@example.test"));
    expect(replace).toHaveBeenCalledWith("/notebooks");
  });
});
