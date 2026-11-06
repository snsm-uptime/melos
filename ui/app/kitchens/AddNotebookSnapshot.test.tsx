/** @vitest-environment jsdom */

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ToastProvider, ToastViewport } from "@/components/Toast";

import { AddNotebookSnapshot } from "./AddNotebookSnapshot";

const notebook = (over: Record<string, unknown>) => ({
  id: "nb-1",
  name: "ana's Notebook",
  kind: "personal",
  owner_alias: "ana",
  access: "owner",
  is_default: true,
  recipe_count: 3,
  kitchen_id: null,
  kitchen_is_archived: null,
  origin_notebook_name: null,
  is_snapshot: false,
  is_own_capture_notebook: false,
  ...over,
});

const list = [
  notebook({}),
  notebook({ id: "nb-2", name: "Desserts", is_default: false }),
  notebook({
    id: "nb-3",
    name: "Family list",
    access: "member",
    is_default: false,
  }),
  notebook({
    id: "nb-4",
    name: "Home notebook",
    kind: "kitchen",
    access: "kitchen_member",
    kitchen_id: "k1",
  }),
];

type Reply = { status: number; body: unknown };

const SNAPSHOTS = "/api/notebooks/kitchens/k1/snapshots";

let posts: {
  confirm_repeat: boolean;
  snapshot_key: string;
  source_notebook_id: string;
}[];
let replies: (Reply | Promise<Reply>)[];
let onAdded: ReturnType<typeof vi.fn<() => void>>;
let container: HTMLDivElement;
let root: Root;
let order: string[];

function answer(reply: Reply) {
  return {
    ok: reply.status >= 200 && reply.status < 300,
    status: reply.status,
    json: async () => reply.body,
  };
}

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

function button(name: string): HTMLButtonElement | undefined {
  return Array.from(document.querySelectorAll("button")).find(
    (el) =>
      el.getAttribute("aria-label") === name || el.textContent?.includes(name),
  );
}

/** The dialog opens by mounting, as the kitchen notebooks screen mounts it. */
function Host() {
  const [open, setOpen] = useState(true);
  return open ? (
    <AddNotebookSnapshot
      kitchenId="k1"
      locale="en"
      onAdded={onAdded}
      onClose={() => setOpen(false)}
    />
  ) : null;
}

async function open() {
  await flush();
}

/** Mounts the dialog again, so it loads with the fetch stubbed in the test. */
async function remount() {
  act(() => root.render(<></>));
  act(() => {
    root.render(
      <ToastProvider>
        <Host />
        <ToastViewport />
      </ToastProvider>,
    );
  });
  await flush();
}

async function choose(name: string) {
  act(() => button(name)!.click());
  await flush();
}

beforeEach(() => {
  posts = [];
  replies = [{ status: 201, body: notebook({ id: "snap", kind: "kitchen" }) }];
  order = [];
  onAdded = vi.fn<() => void>();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      order.push(url);
      if (url === "/api/notebooks/default")
        return answer({ status: 200, body: list[0] });
      if (url === "/api/notebooks")
        return answer({ status: 200, body: { notebooks: list } });
      if (url === SNAPSHOTS) {
        posts.push(JSON.parse(init?.body as string));
        const reply = replies.length > 1 ? replies.shift()! : replies[0];
        return answer(await reply);
      }
      throw new Error(`unexpected call ${url}`);
    }),
  );
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
  act(() => {
    root.render(
      <ToastProvider>
        <Host />
        <ToastViewport />
      </ToastProvider>,
    );
  });
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("AddNotebookSnapshot", () => {
  it("loads the default first, and offers only the personal notebooks the person owns", async () => {
    await open();

    expect(order.slice(0, 2)).toEqual([
      "/api/notebooks/default",
      "/api/notebooks",
    ]);
    expect(button("ana's Notebook")).toBeDefined();
    expect(button("Desserts")).toBeDefined();
    expect(button("Family list")).toBeUndefined();
    expect(button("Home notebook")).toBeUndefined();
  });

  it("says who will see the copy", async () => {
    await open();

    expect(document.body.textContent).toContain(
      "Everyone in this kitchen will see a copy",
    );
  });

  it("adds at once with no confirmation, and reports it to screen readers", async () => {
    await open();

    await choose("Desserts");

    expect(posts).toHaveLength(1);
    expect(posts[0]).toMatchObject({
      source_notebook_id: "nb-2",
      confirm_repeat: false,
    });
    expect(document.querySelector("[role='dialog']")).toBeNull();
    expect(onAdded).toHaveBeenCalledTimes(1);
    expect(document.querySelector("[role='status']")?.textContent).toContain(
      "Desserts was added to this kitchen.",
    );
  });

  it("shows the warning on snapshot_exists, and cancel sends nothing more", async () => {
    replies = [{ status: 409, body: { code: "snapshot_exists" } }];
    await open();

    await choose("Desserts");

    expect(document.body.textContent).toContain(
      "already has a copy of Desserts",
    );
    act(() => button("Cancel")!.click());
    await flush();
    expect(posts).toHaveLength(1);
    expect(onAdded).not.toHaveBeenCalled();
    expect(document.querySelector("[role='dialog']")).toBeNull();
  });

  it("resends the same key when the repeat is confirmed", async () => {
    replies = [
      { status: 409, body: { code: "snapshot_exists" } },
      { status: 201, body: notebook({ id: "snap" }) },
    ];
    await open();
    await choose("Desserts");

    await choose("Add again");

    expect(posts).toHaveLength(2);
    expect(posts[1].snapshot_key).toBe(posts[0].snapshot_key);
    expect(posts[1].confirm_repeat).toBe(true);
    expect(onAdded).toHaveBeenCalledTimes(1);
  });

  it("sends once when pressed twice, and shows that it is running", async () => {
    let finish: (reply: Reply) => void = () => {};
    replies = [new Promise<Reply>((resolve) => (finish = resolve))];
    await open();
    const row = button("Desserts")!;

    act(() => {
      row.click();
      row.click();
    });
    await flush();

    expect(posts).toHaveLength(1);
    expect(button("Desserts")!.disabled).toBe(true);
    expect(document.body.textContent).toContain("Adding your notebook…");

    finish({ status: 201, body: notebook({ id: "snap" }) });
    await flush();
    expect(onAdded).toHaveBeenCalledTimes(1);
  });

  it("shows a message after a failure, and a retry keeps the key", async () => {
    replies = [
      { status: 500, body: {} },
      { status: 201, body: notebook({ id: "snap" }) },
    ];
    await open();

    await choose("Desserts");

    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "Could not add the notebook. Try again.",
    );
    expect(onAdded).not.toHaveBeenCalled();

    await choose("Desserts");

    expect(posts[1].snapshot_key).toBe(posts[0].snapshot_key);
    expect(onAdded).toHaveBeenCalledTimes(1);
  });

  it("uses a new key for a different notebook after a failure", async () => {
    replies = [
      { status: 500, body: {} },
      { status: 201, body: notebook({ id: "snap" }) },
    ];
    await open();
    await choose("Desserts");

    await choose("ana's Notebook");

    expect(posts[1].snapshot_key).not.toBe(posts[0].snapshot_key);
  });

  it("explains when the notebook is gone or the kitchen was archived", async () => {
    replies = [
      { status: 404, body: { code: "notebook_not_found" } },
      { status: 403, body: { code: "kitchen_archived" } },
    ];
    await open();

    await choose("Desserts");
    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "That notebook is no longer available.",
    );

    await choose("Desserts");
    expect(document.querySelector("[role='alert']")?.textContent).toContain(
      "archived",
    );
  });

  it("says so when the person owns no notebooks to add", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) =>
        answer({
          status: 200,
          body: url === "/api/notebooks" ? { notebooks: [list[2]] } : list[0],
        }),
      ),
    );

    await remount();

    expect(document.body.textContent).toContain(
      "You have no notebooks of your own to add.",
    );
  });

  it("shows a load error when the notebooks can't be read", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => answer({ status: 500, body: {} })),
    );

    await remount();

    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "Could not load notebooks. Try again.",
    );
  });
});
