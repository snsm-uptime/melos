/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { recipeFixture } from "@/components/RecipeDetail/fixtures";

import { RecipeEditScreen } from "./RecipeEditScreen";

const router = { push: vi.fn(), replace: vi.fn() };
let search = "";
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => new URLSearchParams(search),
}));

function stub(status: number, body: unknown = {}) {
  const mock = vi.fn(
    async () => new Response(JSON.stringify(body), { status }),
  );
  vi.stubGlobal("fetch", mock);
  return mock;
}

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("RecipeEditScreen", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    search = "from=" + encodeURIComponent("/notebooks/nb1?page=2");
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  async function render() {
    await act(async () => {
      root.render(<RecipeEditScreen recipeId="r1" locale="en" />);
    });
    await flush();
  }

  it("shows the form for a member who can write, with Back to the detail and its list", async () => {
    stub(200, recipeFixture());
    await render();
    expect(container.querySelector<HTMLInputElement>("[aria-label=Title]")?.value).toBe(
      "Tomato rice",
    );
    const back = container.querySelector("a[aria-label=Back]");
    expect(back?.getAttribute("href")).toBe(
      `/recipes/r1?from=${encodeURIComponent("/notebooks/nb1?page=2")}`,
    );
  });

  it("shows no form to a member who can only read", async () => {
    stub(200, recipeFixture({ can_write: false }));
    await render();
    expect(container.textContent).toContain("You can only read this recipe.");
    expect(container.querySelector("[aria-label=Title]")).toBeNull();
  });

  it("says the recipe is no longer available on a 404", async () => {
    stub(404, { code: "recipe_not_found" });
    await render();
    expect(container.textContent).toContain("That recipe is no longer available.");
  });

  describe("edit lock (spec 022)", () => {
    function route(lock: { status: number; body: unknown }) {
      const mock = vi.fn(async (url: string, init?: RequestInit) => {
        if (url.endsWith("/edit-lock")) {
          if (init?.method === "DELETE") return new Response(null, { status: 204 });
          return new Response(JSON.stringify(lock.body), { status: lock.status });
        }
        return new Response(JSON.stringify(recipeFixture()), { status: 200 });
      });
      vi.stubGlobal("fetch", mock);
      return mock;
    }

    const calls = (mock: ReturnType<typeof route>, method: string) =>
      mock.mock.calls.filter(
        ([url, init]) => String(url).endsWith("/edit-lock") && init?.method === method,
      );

    it("takes the lock on open and frees it on leaving", async () => {
      const mock = route({
        status: 200,
        body: { editor: { alias: "ana", is_me: true, idle_expires_at: "2999-01-01T00:00:00Z" } },
      });
      await render();
      expect(calls(mock, "POST")).toHaveLength(1);
      expect(container.querySelector("[aria-label=Title]")).not.toBeNull();
      act(() => root.unmount());
      expect(calls(mock, "DELETE")).toHaveLength(1);
      root = createRoot(container);
    });

    it("shows a read-only page with the editor when someone else edits", async () => {
      route({ status: 409, body: { code: "recipe_locked", editor_alias: "ben" } });
      await render();
      expect(container.textContent).toContain("ben is editing this recipe");
      expect(container.querySelector("[aria-label=Title]")).toBeNull();
      expect(container.querySelector("a")?.getAttribute("href")).toContain("/recipes/r1");
    });

    it("warns a minute before the idle limit and keeps the lock alive on request", async () => {
      const soon = new Date(Date.now() + 30_000).toISOString();
      const mock = route({
        status: 200,
        body: { editor: { alias: "ana", is_me: true, idle_expires_at: soon } },
      });
      await render();
      expect(container.textContent).toContain(
        "Your recipe changes will be discarded in 1 minute",
      );
      const keep = Array.from(container.querySelectorAll("button")).find(
        (b) => b.textContent === "Keep editing",
      );
      await act(async () => keep?.click());
      expect(calls(mock, "POST")).toHaveLength(2);
    });
  });
});
