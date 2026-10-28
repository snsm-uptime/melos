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
    const back = Array.from(container.querySelectorAll("a")).find((a) =>
      a.textContent?.includes("Back"),
    );
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
});
