/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { KitchenNotebooksSection } from "./KitchenNotebooksSection";

const replace = vi.fn();
const router = { replace };

vi.mock("next/navigation", () => ({
  useRouter: () => router,
}));

const kitchenId = "5e7b0c1a-0000-4000-8000-000000000001";

const homeNotebook = {
  id: "c3d0-1",
  name: "ana's (Home) Notebook",
  kind: "kitchen",
  owner_alias: "ana",
  access: "kitchen_member",
  is_default: false,
  kitchen_id: kitchenId,
  kitchen_is_archived: false,
};

const secondNotebook = {
  id: "c3d0-2",
  name: "Weekend list",
  kind: "kitchen",
  owner_alias: null,
  access: "kitchen_member",
  is_default: false,
  kitchen_id: kitchenId,
  kitchen_is_archived: false,
};

type Reply = { status: number; body: unknown };

function stubBff(queue: Reply[]) {
  const fetchMock = vi.fn(async () => {
    const reply = queue.length > 1 ? queue.shift()! : queue[0];
    return {
      ok: reply.status >= 200 && reply.status < 300,
      status: reply.status,
      json: async () => reply.body,
    };
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("KitchenNotebooksSection", () => {
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

  function render(isArchived = false, viewerAlias: string | null = "ben") {
    act(() => {
      root.render(
        <KitchenNotebooksSection
          kitchenId={kitchenId}
          isArchived={isArchived}
          viewerAlias={viewerAlias}
          locale="en"
        />,
      );
    });
  }

  it("hides the owner line on a notebook the viewer owns", async () => {
    stubBff([{ status: 200, body: { notebooks: [homeNotebook, secondNotebook] } }]);

    render(false, "ana");
    await flush();

    expect(container.textContent).not.toContain("Owned by ana");
    expect(container.textContent).toContain("Owned by unknown");
  });

  it("calls the kitchen notebooks path for the kitchen", async () => {
    const fetchMock = stubBff([{ status: 200, body: { notebooks: [homeNotebook] } }]);

    render();
    await flush();

    const [url] = fetchMock.mock.calls[0] as unknown as [string];
    expect(url).toBe(`/api/notebooks/kitchens/${kitchenId}`);
  });

  it("shows the kitchen not-found message and no cards on 404 kitchen_not_found", async () => {
    stubBff([{ status: 404, body: { code: "kitchen_not_found" } }]);

    render();
    await flush();

    expect(container.querySelector('[role="alert"]')?.textContent).toBe(
      "This kitchen is unavailable.",
    );
    expect(container.querySelector("h3")).toBeNull();
  });

  it("shows the empty state when the kitchen has no notebooks", async () => {
    stubBff([{ status: 200, body: { notebooks: [] } }]);

    render();
    await flush();

    expect(container.textContent).toContain("This kitchen has no notebooks yet.");
    expect(container.querySelector("h3")).toBeNull();
  });

  it("shows name and owner only, keeps the order given, and renders no action", async () => {
    stubBff([{ status: 200, body: { notebooks: [homeNotebook, secondNotebook] } }]);

    render();
    await flush();

    const names = Array.from(container.querySelectorAll("h3")).map((h) => h.textContent);
    expect(names).toEqual(["ana's (Home) Notebook", "Weekend list"]);
    expect(container.textContent).toContain("Owned by ana");
    expect(container.textContent).toContain("Owned by unknown");
    expect(container.textContent).not.toContain("Kitchen member");
    expect(container.textContent).not.toContain("Default");
    expect(container.querySelectorAll("a, button").length).toBe(0);
  });

  it("renders no add-recipe action in an archived kitchen, and still lists its notebooks", async () => {
    stubBff([{ status: 200, body: { notebooks: [{ ...homeNotebook, kitchen_is_archived: true }] } }]);

    render(true);
    await flush();

    expect(container.querySelector("h3")?.textContent).toBe("ana's (Home) Notebook");
    expect(container.querySelectorAll("a, button").length).toBe(0);
  });

  it("redirects to the alias step on 403 alias_required and shows no cards", async () => {
    stubBff([{ status: 403, body: { code: "alias_required" } }]);

    render();
    await flush();

    expect(replace).toHaveBeenCalledWith(`/alias?returnTo=${encodeURIComponent(`/kitchens/${kitchenId}`)}`);
    expect(container.querySelector("h3")).toBeNull();
    expect(container.querySelector('[role="alert"]')).toBeNull();
  });

  it("shows the loading error with retry on other failures, and retry reloads", async () => {
    const fetchMock = stubBff([
      { status: 500, body: { detail: "boom" } },
      { status: 200, body: { notebooks: [homeNotebook] } },
    ]);

    render();
    await flush();
    expect(container.querySelector('[role="alert"]')?.textContent).toBe(
      "Could not load notebooks. Try again.",
    );

    await act(async () => {
      (container.querySelector("button") as HTMLButtonElement).click();
    });
    await flush();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.querySelector("h3")?.textContent).toBe("ana's (Home) Notebook");
  });

  it("drops the error while a retry is loading", async () => {
    let calls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(() => {
        calls += 1;
        if (calls === 1) {
          return Promise.resolve({ ok: false, status: 500, json: async () => ({}) });
        }
        return new Promise(() => {});
      }),
    );

    render();
    await flush();
    expect(container.querySelector('[role="alert"]')).not.toBeNull();

    await act(async () => {
      (container.querySelector("button") as HTMLButtonElement).click();
    });

    expect(container.querySelector('[role="alert"]')).toBeNull();
    expect(container.querySelector("h3")).toBeNull();
  });
});
