/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ChromeBackProvider,
  useChromeHeaderState,
} from "@/components/ChromeBack";
import { ToastProvider } from "@/components/Toast";

import { KitchenNotebooksScreen } from "./KitchenNotebooksScreen";

const replace = vi.fn();
const router = { replace };
const { requestSidePanelRefresh } = vi.hoisted(() => ({
  requestSidePanelRefresh: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => router,
  usePathname: () => "/kitchens/k1/notebooks",
}));
vi.mock("@/lib/sidePanelClient", () => ({ requestSidePanelRefresh }));
vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    ...rest
  }: {
    href: string;
    children: React.ReactNode;
  }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const kitchenNotebook = (over: Record<string, unknown>) => ({
  id: "nb-1",
  name: "ana's (Home) Notebook",
  kind: "kitchen",
  owner_alias: "ana",
  access: "kitchen_member",
  is_default: false,
  recipe_count: 2,
  kitchen_id: "k1",
  kitchen_is_archived: false,
  origin_notebook_name: null,
  is_snapshot: false,
  is_own_capture_notebook: true,
  ...over,
});

type Reply = { status: number; body: unknown };

let replies: Reply[];
let container: HTMLDivElement;
let root: Root;

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function reply(item: Reply) {
  return {
    ok: item.status >= 200 && item.status < 300,
    status: item.status,
    json: async () => item.body,
  };
}

/** Shows the chrome header's trailing actions, which AppShell draws in the real page. */
function ChromeProbe() {
  const header = useChromeHeaderState();
  return <div data-testid="chrome">{header.trailing}</div>;
}

async function render() {
  act(() => {
    root.render(
      <ToastProvider>
        <ChromeBackProvider>
          <ChromeProbe />
          <KitchenNotebooksScreen
            kitchenId="k1"
            locale="en"
            viewerAlias="ana"
          />
        </ChromeBackProvider>
      </ToastProvider>,
    );
  });
  await flush();
}

function links(): (string | null)[] {
  return Array.from(document.querySelectorAll("a")).map((el) =>
    el.getAttribute("href"),
  );
}

/** The add actions are in the chrome header (not the grid). */
function chromeButton(label: string): HTMLButtonElement | null {
  return document.querySelector(
    `[data-testid='chrome'] button[aria-label='${label}']`,
  );
}

function addButton(): HTMLButtonElement | null {
  return chromeButton("Add a notebook");
}

beforeEach(() => {
  replace.mockReset();
  requestSidePanelRefresh.mockReset();
  replies = [{ status: 200, body: { notebooks: [kitchenNotebook({})] } }];
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      reply(replies.length > 1 ? replies.shift()! : replies[0]),
    ),
  );
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("KitchenNotebooksScreen", () => {
  const newTile = () => chromeButton("New notebook");

  it("offers a new notebook in an active kitchen", async () => {
    await render();

    expect(newTile()).toBeDefined();
  });

  it("offers no new notebook in an archived kitchen", async () => {
    replies = [
      {
        status: 200,
        body: { notebooks: [kitchenNotebook({ kitchen_is_archived: true })] },
      },
    ];
    await render();

    expect(newTile()).toBeNull();
  });

  it("shows every notebook as a card linking to its page, empty ones included", async () => {
    replies = [
      {
        status: 200,
        body: {
          notebooks: [
            kitchenNotebook({}),
            kitchenNotebook({
              id: "snap",
              name: "Desserts",
              recipe_count: 0,
              is_snapshot: true,
            }),
          ],
        },
      },
    ];

    await render();

    expect(links()).toEqual([
      `/notebooks/nb-1?from=${encodeURIComponent("/kitchens/k1/notebooks")}`,
      `/notebooks/snap?from=${encodeURIComponent("/kitchens/k1/notebooks")}`,
    ]);
    expect(document.body.textContent).toContain("Desserts");
    expect(document.body.textContent).toContain("0 recipes");
  });

  it("puts both add actions in the chrome, leaves the grid to notebooks, and shows no access chip", async () => {
    await render();

    expect(addButton()).not.toBeNull();
    expect(newTile()).not.toBeNull();
    expect(document.querySelector("li:first-child")?.textContent).toContain(
      "ana's (Home) Notebook",
    );
    expect(document.body.textContent).not.toContain("Kitchen member");
  });

  it("shows the cards with no add action in an archived kitchen", async () => {
    replies = [
      {
        status: 200,
        body: { notebooks: [kitchenNotebook({ kitchen_is_archived: true })] },
      },
    ];

    await render();

    expect(links()).toHaveLength(1);
    expect(addButton()).toBeNull();
  });

  it("shows no add action when an archived kitchen has no notebooks", async () => {
    replies = [{ status: 200, body: { notebooks: [] } }];

    await render();

    expect(document.body.textContent).toContain(
      "This kitchen has no notebooks yet.",
    );
    expect(addButton()).toBeNull();
  });

  it("shows a new snapshot without a page reload, and refreshes the side panel", async () => {
    const before = { status: 200, body: { notebooks: [kitchenNotebook({})] } };
    const snapshot = kitchenNotebook({
      id: "snap",
      name: "Desserts",
      is_snapshot: true,
    });
    const after = {
      status: 200,
      body: { notebooks: [kitchenNotebook({}), snapshot] },
    };
    const personal = kitchenNotebook({
      id: "p1",
      name: "Desserts",
      kind: "personal",
      access: "owner",
    });
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        if (url === "/api/notebooks/default")
          return reply({ status: 200, body: personal });
        if (url === "/api/notebooks") {
          return reply({ status: 200, body: { notebooks: [personal] } });
        }
        if (init?.method === "POST")
          return reply({ status: 201, body: snapshot });
        const added = vi
          .mocked(fetch)
          .mock.calls.some(([, call]) => call?.method === "POST");
        return reply(added ? after : before);
      }),
    );
    await render();
    expect(links()).toHaveLength(1);

    act(() => addButton()!.click());
    await flush();
    const row = Array.from(
      document.querySelectorAll("[role='dialog'] button"),
    ).find((el) => el.textContent?.includes("Desserts")) as HTMLButtonElement;
    act(() => row.click());
    await flush();

    expect(links()).toHaveLength(2);
    expect(requestSidePanelRefresh).toHaveBeenCalledTimes(1);
  });

  it("shows not found for someone outside the kitchen", async () => {
    replies = [{ status: 404, body: { code: "kitchen_not_found" } }];

    await render();

    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "This kitchen is unavailable.",
    );
  });

  it("sends a person with no alias to the alias step", async () => {
    replies = [{ status: 403, body: { code: "alias_required" } }];

    await render();

    expect(replace).toHaveBeenCalledWith(
      `/alias?returnTo=${encodeURIComponent("/kitchens/k1/notebooks")}`,
    );
  });

  it("offers a retry when the notebooks can't be read", async () => {
    replies = [
      { status: 500, body: {} },
      { status: 200, body: { notebooks: [kitchenNotebook({})] } },
    ];
    await render();

    const retry = Array.from(document.querySelectorAll("button")).find(
      (el) => el.textContent === "Try again",
    ) as HTMLButtonElement;
    act(() => retry.click());
    await flush();

    expect(links()).toHaveLength(1);
  });
});
