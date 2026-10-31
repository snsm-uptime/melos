/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearCapture, markSaved } from "@/lib/capture/captureStore";

import { AppShell } from "@/components/AppShell";

import { NotebookTabScreen } from "./NotebookTabScreen";

const replace = vi.fn();
const router = { replace };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/notebooks",
}));

vi.mock("@/components/PreferencesProvider", () => ({
  usePreferences: () => ({ locale: "en", theme: "light" }),
  useOptionalPreferences: () => ({ locale: "en" }),
}));

const defaultNotebook = {
  id: "nb-default",
  name: "ana's Notebook",
  kind: "personal",
  owner_alias: "ana",
  access: "owner",
  is_default: true,
  recipe_count: 0,
  kitchen_id: null,
  kitchen_is_archived: null,
};

const sharedNotebook = {
  id: "nb-shared",
  name: "Family list",
  kind: "personal",
  owner_alias: "ben",
  access: "member",
  is_default: false,
  recipe_count: 0,
  kitchen_id: null,
  kitchen_is_archived: null,
};

type Reply = { status: number; body: unknown };

/** Each BFF path answers with the next reply queued for it; the last reply repeats. */
function stubBff(replies: Record<string, Reply[]>) {
  const calls: string[] = [];
  const fetchMock = vi.fn(async (url: string) => {
    calls.push(url);
    const queue = replies[url];
    if (!queue) throw new Error(`unexpected call ${url}`);
    const reply = queue.length > 1 ? queue.shift()! : queue[0];
    return {
      ok: reply.status >= 200 && reply.status < 300,
      status: reply.status,
      json: async () => reply.body,
    };
  });
  vi.stubGlobal("fetch", fetchMock);
  return { calls, fetchMock };
}

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("NotebookTabScreen", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    replace.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
    vi.unstubAllGlobals();
  });

  function render(viewerAlias: string | null = "ben") {
    act(() => {
      root.render(<NotebookTabScreen locale="en" viewerAlias={viewerAlias} />);
    });
  }

  it("puts the title in the shared header, not in the page body", async () => {
    stubBff({
      "/api/notebooks/default": [{ status: 200, body: defaultNotebook }],
      "/api/notebooks": [{ status: 200, body: { notebooks: [defaultNotebook] } }],
    });

    act(() => {
      root.render(
        <AppShell>
          <NotebookTabScreen locale="en" viewerAlias="ana" />
        </AppShell>,
      );
    });
    await flush();

    const header = container.querySelector('[data-app-chrome="header"]') as HTMLElement;
    expect(header.querySelector("h1")?.textContent).toBe("Notebook");
    expect(header.querySelector('a[href="/account"]')).toBeNull();
    expect(container.querySelectorAll("h1")).toHaveLength(1);
  });

  it("hides the owner line on cards the viewer owns and shows it on the rest", async () => {
    stubBff({
      "/api/notebooks/default": [{ status: 200, body: defaultNotebook }],
      "/api/notebooks": [{ status: 200, body: { notebooks: [defaultNotebook, sharedNotebook] } }],
    });

    render("ana");
    await flush();

    expect(container.textContent).not.toContain("Owned by ana");
    expect(container.textContent).toContain("Owned by ben");
  });

  it("shows \"Recipe saved\" once after a save returned here", async () => {
    stubBff({
      "/api/notebooks/default": [{ status: 200, body: defaultNotebook }],
      "/api/notebooks": [{ status: 200, body: { notebooks: [defaultNotebook] } }],
    });
    clearCapture();
    markSaved("/notebooks");

    render();
    await flush();
    expect(container.textContent).toContain("Recipe saved");

    act(() => root.unmount());
    root = createRoot(container);
    render();
    await flush();
    expect(container.textContent).not.toContain("Recipe saved");
  });

  it("shows no notice when the save returned to another page", async () => {
    stubBff({
      "/api/notebooks/default": [{ status: 200, body: defaultNotebook }],
      "/api/notebooks": [{ status: 200, body: { notebooks: [defaultNotebook] } }],
    });
    clearCapture();
    markSaved("/kitchens/k1");

    render();
    await flush();
    expect(container.textContent).not.toContain("Recipe saved");
  });

  it("calls the default before the list and shows the cards in the order given", async () => {
    const { calls } = stubBff({
      "/api/notebooks/default": [{ status: 200, body: defaultNotebook }],
      "/api/notebooks": [{ status: 200, body: { notebooks: [defaultNotebook, sharedNotebook] } }],
    });

    render();
    await flush();

    expect(calls).toEqual(["/api/notebooks/default", "/api/notebooks"]);
    const names = Array.from(container.querySelectorAll("h3")).map((h) => h.textContent);
    expect(names).toEqual(["ana's Notebook", "Family list"]);
    expect(container.textContent).toContain("Default");
    // Each card links to its recipe list (S-021).
    const hrefs = Array.from(container.querySelectorAll("a")).map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual(["/notebooks/nb-default", "/notebooks/nb-shared"]);
  });

  it("puts the add-recipe call to action in the first cell, before the cards", async () => {
    stubBff({
      "/api/notebooks/default": [{ status: 200, body: defaultNotebook }],
      "/api/notebooks": [{ status: 200, body: { notebooks: [defaultNotebook, sharedNotebook] } }],
    });

    render();
    await flush();

    const cells = container.querySelectorAll("ul > li");
    expect(cells).toHaveLength(3);
    const add = cells[0].querySelector("button") as HTMLButtonElement;
    expect(add.getAttribute("aria-label")).toBe("Add a recipe");
    expect(add.disabled).toBe(false);
    expect(cells[0].querySelector("h3")).toBeNull();
  });

  it("shows the empty state when the list is empty", async () => {
    stubBff({
      "/api/notebooks/default": [{ status: 200, body: defaultNotebook }],
      "/api/notebooks": [{ status: 200, body: { notebooks: [] } }],
    });

    render();
    await flush();

    expect(container.textContent).toContain("No notebooks yet.");
    expect(container.querySelector("h3")).toBeNull();
  });

  it("shows the loading error with retry and does not call the list when the default fails", async () => {
    const { calls } = stubBff({
      "/api/notebooks/default": [{ status: 502, body: { code: "bad_gateway" } }],
      "/api/notebooks": [{ status: 200, body: { notebooks: [sharedNotebook] } }],
    });

    render();
    await flush();

    expect(calls).toEqual(["/api/notebooks/default"]);
    expect(container.querySelector('[role="alert"]')?.textContent).toBe(
      "Could not load notebooks. Try again.",
    );
    expect(container.querySelector("h3")).toBeNull();
    expect(replace).not.toHaveBeenCalled();
  });

  it("redirects to the alias step on 403 alias_required from the default", async () => {
    const { calls } = stubBff({
      "/api/notebooks/default": [{ status: 403, body: { code: "alias_required" } }],
      "/api/notebooks": [{ status: 200, body: { notebooks: [] } }],
    });

    render();
    await flush();

    expect(replace).toHaveBeenCalledWith("/alias?returnTo=%2Fnotebooks");
    expect(calls).toEqual(["/api/notebooks/default"]);
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("redirects to the alias step on 403 alias_required from the list", async () => {
    stubBff({
      "/api/notebooks/default": [{ status: 200, body: defaultNotebook }],
      "/api/notebooks": [{ status: 403, body: { code: "alias_required" } }],
    });

    render();
    await flush();

    expect(replace).toHaveBeenCalledWith("/alias?returnTo=%2Fnotebooks");
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("retry re-runs the default and then the list, and shows the cards", async () => {
    const { calls } = stubBff({
      "/api/notebooks/default": [
        { status: 502, body: { code: "bad_gateway" } },
        { status: 200, body: defaultNotebook },
      ],
      "/api/notebooks": [{ status: 200, body: { notebooks: [defaultNotebook] } }],
    });

    render();
    await flush();
    expect(container.querySelector('[role="alert"]')).not.toBeNull();

    const retry = container.querySelector("button") as HTMLButtonElement;
    await act(async () => {
      retry.click();
    });
    await flush();

    expect(calls).toEqual([
      "/api/notebooks/default",
      "/api/notebooks/default",
      "/api/notebooks",
    ]);
    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.querySelector("h3")?.textContent).toBe("ana's Notebook");
  });

  it("drops the error while a retry is loading, so no stale state stays on screen", async () => {
    let resolveRetry: (value: unknown) => void = () => {};
    let defaultCalls = 0;
    const fetchMock = vi.fn((url: string) => {
      if (url === "/api/notebooks/default") {
        defaultCalls += 1;
        if (defaultCalls === 1) {
          return Promise.resolve({ ok: false, status: 502, json: async () => ({}) });
        }
        return new Promise((resolve) => {
          resolveRetry = resolve;
        });
      }
      return Promise.resolve({ ok: true, status: 200, json: async () => ({ notebooks: [] }) });
    });
    vi.stubGlobal("fetch", fetchMock);

    render();
    await flush();
    expect(container.querySelector('[role="alert"]')).not.toBeNull();

    await act(async () => {
      (container.querySelector("button") as HTMLButtonElement).click();
    });

    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.querySelector("h3")).toBeNull();

    await act(async () => {
      resolveRetry({ ok: true, status: 200, json: async () => defaultNotebook });
    });
    await flush();
    expect(container.textContent).toContain("No notebooks yet.");
  });
});
