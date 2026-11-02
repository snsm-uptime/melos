/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NotebookDeleteDialog } from "./NotebookDeleteDialog";

const replace = vi.fn();
const router = { replace };
const { requestSidePanelRefresh } = vi.hoisted(() => ({ requestSidePanelRefresh: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/lib/sidePanelClient", () => ({ requestSidePanelRefresh }));

const personal = {
  id: "nb-1",
  name: "Soups",
  kind: "personal",
  access: "owner",
  is_default: false,
  recipe_count: 12,
  kitchen_id: null,
  kitchen_is_archived: null,
};
const owner = { user_id: "u1", alias: "ana", role: "owner", is_self: true };
const member = { user_id: "u2", alias: "ben", role: "member", is_self: false };

type Reply = { status: number; body?: unknown } | "offline";

describe("NotebookDeleteDialog", () => {
  let container: HTMLDivElement;
  let root: Root;
  const onClose = vi.fn();

  beforeEach(() => {
    replace.mockReset();
    onClose.mockReset();
    requestSidePanelRefresh.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  function answer(reply: Reply) {
    if (reply === "offline") throw new Error("offline");
    return {
      ok: reply.status < 300,
      status: reply.status,
      json: async () => reply.body,
    };
  }

  async function open(handlers: { notebook: Reply; members?: Reply; remove?: Reply }) {
    const calls: { url: string; method: string }[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const method = init?.method ?? "GET";
        calls.push({ url, method });
        if (method === "DELETE") return answer(handlers.remove ?? { status: 204 });
        return answer(url.endsWith("/members") ? handlers.members! : handlers.notebook);
      }),
    );
    await act(async () => {
      root.render(
        <NotebookDeleteDialog
          notebookId="nb-1"
          notebookName="Old name"
          goneHref="/notebooks"
          locale="en"
          onClose={onClose}
        />,
      );
    });
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    return calls;
  }

  const button = (name: string) =>
    Array.from(container.querySelectorAll("button")).find(
      (el) => el.textContent === name,
    ) as HTMLButtonElement;
  const alert = () => container.querySelector('[role="alert"]')?.textContent;

  async function click(el: Element) {
    await act(async () => {
      el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }

  it("names the notebook, its recipes and the people who lose access", async () => {
    await open({
      notebook: { status: 200, body: personal },
      members: { status: 200, body: { members: [owner, member, { ...member, user_id: "u3" }] } },
    });
    expect(container.textContent).toContain("Delete Soups?");
    expect(container.textContent).toContain("This deletes 12 recipes. This can't be undone.");
    expect(container.textContent).toContain("2 people will lose access.");
    expect(container.textContent).not.toContain("take its place");
  });

  it("has no people line with no members, and says so for one recipe and one person", async () => {
    await open({
      notebook: { status: 200, body: { ...personal, recipe_count: 1 } },
      members: { status: 200, body: { members: [owner] } },
    });
    expect(container.textContent).toContain("This deletes 1 recipe.");
    expect(container.textContent).not.toContain("lose access");
  });

  it("says one person, and handles an empty notebook", async () => {
    await open({
      notebook: { status: 200, body: { ...personal, recipe_count: 0 } },
      members: { status: 200, body: { members: [owner, member] } },
    });
    expect(container.textContent).toContain("It has no recipes.");
    expect(container.textContent).toContain("1 person will lose access.");
  });

  it("says a new one takes the place of a default notebook", async () => {
    await open({
      notebook: { status: 200, body: { ...personal, is_default: true } },
      members: { status: 200, body: { members: [owner] } },
    });
    expect(container.textContent).toContain("A new, empty notebook will take its place.");
  });

  it("reads no members for a kitchen notebook", async () => {
    const calls = await open({
      notebook: { status: 200, body: { ...personal, kind: "kitchen", kitchen_id: "k1" } },
    });
    expect(calls.map((call) => call.url)).toEqual(["/api/notebooks/nb-1"]);
    expect(button("Delete")).toBeDefined();
  });

  it("offers no confirm until both reads have answered", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    await act(async () => {
      root.render(
        <NotebookDeleteDialog
          notebookId="nb-1"
          notebookName="Old name"
          goneHref="/notebooks"
          locale="en"
          onClose={onClose}
        />,
      );
    });
    expect(button("Delete")).toBeUndefined();
    expect(button("Cancel")).toBeDefined();
  });

  it.each(["notebook", "members"] as const)(
    "a 404 on the %s read says it is gone, and closing leaves",
    async (read) => {
      const gone = { status: 404, body: { code: "notebook_not_found" } };
      await open({
        notebook: read === "notebook" ? gone : { status: 200, body: personal },
        members: gone,
      });
      expect(alert()).toBe("This notebook no longer exists.");
      await click(button("Close"));
      expect(replace).toHaveBeenCalledWith("/notebooks");
    },
  );

  it.each(["notebook", "members"] as const)(
    "any other failed %s read gives no confirm and keeps Cancel",
    async (read) => {
      await open({
        notebook: read === "notebook" ? "offline" : { status: 200, body: personal },
        members: { status: 500, body: {} },
      });
      expect(alert()).toBe("Could not check what this notebook holds. Try again.");
      expect(button("Delete")).toBeUndefined();
      await click(button("Cancel"));
      expect(onClose).toHaveBeenCalled();
    },
  );

  it("deletes nothing on Cancel", async () => {
    const calls = await open({
      notebook: { status: 200, body: personal },
      members: { status: 200, body: { members: [owner] } },
    });
    await click(button("Cancel"));
    expect(calls.some((call) => call.method === "DELETE")).toBe(false);
    expect(onClose).toHaveBeenCalled();
  });

  it("deletes, refreshes the side panel and goes to the gone address", async () => {
    const calls = await open({
      notebook: { status: 200, body: personal },
      members: { status: 200, body: { members: [owner] } },
    });
    await click(button("Delete"));
    expect(calls).toContainEqual({ url: "/api/notebooks/nb-1", method: "DELETE" });
    expect(requestSidePanelRefresh).toHaveBeenCalled();
    expect(replace).toHaveBeenCalledWith("/notebooks");
  });

  it("a 404 on the delete says it is gone", async () => {
    await open({
      notebook: { status: 200, body: personal },
      members: { status: 200, body: { members: [owner] } },
      remove: { status: 404, body: { code: "notebook_not_found" } },
    });
    await click(button("Delete"));
    expect(alert()).toBe("This notebook no longer exists.");
    await click(button("Close"));
    expect(replace).toHaveBeenCalledWith("/notebooks");
    expect(requestSidePanelRefresh).not.toHaveBeenCalled();
  });

  it("any other failed delete says so and stays open", async () => {
    await open({
      notebook: { status: 200, body: personal },
      members: { status: 200, body: { members: [owner] } },
      remove: { status: 500, body: {} },
    });
    await click(button("Delete"));
    expect(alert()).toBe("Could not delete the notebook. It has not changed. Try again.");
    expect(button("Delete")).toBeDefined();
    expect(replace).not.toHaveBeenCalled();
  });
});
