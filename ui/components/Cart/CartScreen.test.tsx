/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const replace = vi.fn();
const router = { replace };
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/components/ChromeBack", () => ({ useChromeHeader: () => {} }));

const { client } = vi.hoisted(() => ({
  client: {
    fetchCart: vi.fn(),
    startCartEdit: vi.fn(),
    putCartDraft: vi.fn(),
    saveCart: vi.fn(),
    discardCart: vi.fn(),
  },
}));
vi.mock("@/lib/cartClient", () => client);

import { ToastProvider, ToastViewport } from "@/components/Toast";

import { CartScreen, DRAFT_DEBOUNCE_MS } from "./CartScreen";
import { cart, entry, mount, type } from "./testRoot";

const editing = cart({
  editor: { alias: "ana", is_me: true, idle_expires_at: "2999-01-01T00:00:00Z" },
  draft: { people: 2, people_is_default: true, entries: [entry("a")], dropped_recipe_ids: [] },
  entries: [entry("a")],
});

async function flush() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
}

function click(container: HTMLElement, label: string) {
  const button = Array.from(container.querySelectorAll("button")).find(
    (b) => b.textContent === label,
  );
  act(() => button?.click());
}

describe("CartScreen", () => {
  let view: ReturnType<typeof mount>;

  beforeEach(() => {
    vi.useFakeTimers();
    view = mount();
    replace.mockReset();
    for (const fn of Object.values(client)) fn.mockReset();
    client.fetchCart.mockResolvedValue({ ok: true, value: cart({ entries: [entry("a")] }) });
  });
  afterEach(() => {
    view.unmount();
    vi.useRealTimers();
  });

  async function render() {
    view.render(
      <ToastProvider>
        <CartScreen kitchenId="k1" locale="en" />
        <ToastViewport />
      </ToastProvider>,
    );
    await flush();
  }

  it("loads the saved cart", async () => {
    await render();
    expect(client.fetchCart).toHaveBeenCalledWith("k1");
    expect(view.container.textContent).toContain("Recipe a");
  });

  it("shows the not-found text on 404", async () => {
    client.fetchCart.mockResolvedValue({ ok: false, status: 404, code: "kitchen_not_found" });
    await render();
    expect(view.container.querySelector('[role="alert"]')?.textContent).toBe(
      "This kitchen is unavailable.",
    );
  });

  it("starts editing, sends one debounced draft, then saves", async () => {
    client.startCartEdit.mockResolvedValue({ ok: true, value: editing });
    client.putCartDraft.mockResolvedValue({ ok: true, value: editing });
    client.saveCart.mockResolvedValue({
      ok: true,
      value: { ...cart({ entries: [entry("a", { meals: 3 })] }), dropped_recipe_ids: [] },
    });
    await render();
    click(view.container, "Edit");
    await flush();
    const viewport = () => view.container.querySelector("[data-toast-viewport]");
    expect(viewport()?.textContent).toContain("You're editing the cart.");
    const meals = view.container.querySelectorAll("input")[1] as HTMLInputElement;
    type(meals, "2");
    type(meals, "3");
    expect(client.putCartDraft).not.toHaveBeenCalled();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DRAFT_DEBOUNCE_MS);
    });
    expect(client.putCartDraft).toHaveBeenCalledTimes(1);
    expect(client.putCartDraft).toHaveBeenCalledWith("k1", {
      people: null,
      items: [{ recipe_id: "a", meals: 3 }],
    });
    click(view.container, "Save");
    await flush();
    expect(client.saveCart).toHaveBeenCalledWith("k1");
    expect(view.container.textContent).toContain("Meals 3");
    expect(viewport()).toBeNull();
  });

  it("says the changes were discarded when the lock was lost", async () => {
    client.fetchCart.mockResolvedValue({ ok: true, value: editing });
    client.saveCart.mockResolvedValue({ ok: false, status: 409, code: "not_editing" });
    await render();
    client.fetchCart.mockResolvedValue({ ok: true, value: cart({ entries: [entry("a")] }) });
    click(view.container, "Save");
    await flush();
    expect(view.container.textContent).toContain("Your cart changes were discarded");
    expect(view.container.textContent).toContain("Edit");
  });

  it("reloads when the window gets focus again", async () => {
    await render();
    act(() => {
      window.dispatchEvent(new Event("focus"));
    });
    await flush();
    expect(client.fetchCart).toHaveBeenCalledTimes(2);
  });
});
