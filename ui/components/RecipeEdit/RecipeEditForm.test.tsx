/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { recipeFixture } from "@/components/RecipeDetail/fixtures";

import { RecipeEditForm } from "./RecipeEditForm";

const push = vi.fn();
const router = { push, replace: vi.fn() };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

type Reply = { status: number; body?: unknown };
type Call = { url: string; method: string; body: unknown };

let calls: Call[];
let replies: { match: Reply[]; put: Reply[] };
let release: (() => void) | null;

function stubFetch() {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      calls.push({ url, method, body: init?.body ? JSON.parse(String(init.body)) : undefined });
      if (release) await new Promise<void>((resolve) => (release = resolve));
      const queue = url.endsWith("/name-matches") ? replies.match : replies.put;
      const reply = queue.length > 1 ? (queue.shift() as Reply) : queue[0];
      return new Response(JSON.stringify(reply.body ?? {}), { status: reply.status });
    }),
  );
}

function setValue(element: HTMLInputElement | HTMLTextAreaElement, value: string) {
  const proto = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement : HTMLInputElement;
  Object.getOwnPropertyDescriptor(proto.prototype, "value")?.set?.call(element, value);
  element.dispatchEvent(new Event("input", { bubbles: true }));
}

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe("RecipeEditForm", () => {
  let container: HTMLDivElement;
  let root: Root;
  const onReload = vi.fn();
  const recipe = recipeFixture();

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    push.mockReset();
    onReload.mockReset();
    release = null;
    replies = { match: [{ status: 200, body: { matches: [] } }], put: [{ status: 200, body: recipe }] };
    stubFetch();
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  function render() {
    act(() => {
      root.render(
        <RecipeEditForm
          recipe={recipe}
          locale="en"
          detailHref="/recipes/r1?from=%2Fnotebooks%2Fnb1"
          listHref="/notebooks/nb1"
          onReload={onReload}
        />,
      );
    });
  }

  const byLabel = (label: string) =>
    Array.from(document.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>(`[aria-label="${label}"]`));
  const button = (text: string) =>
    Array.from(document.querySelectorAll("button")).find((b) => b.textContent?.trim() === text);
  const link = (text: string) =>
    Array.from(document.querySelectorAll("a")).find((a) => a.textContent?.includes(text));
  const names = () => byLabel("Name").map((input) => input.value);

  async function save() {
    await act(async () => button("Save")?.click());
    await flush();
  }

  async function leaveName(index: number, value: string) {
    const input = byLabel("Name")[index];
    act(() => setValue(input, value));
    await act(async () => {
      input.dispatchEvent(new FocusEvent("focusout", { bubbles: true }));
    });
    await flush();
  }

  it("shows the stored recipe: title, servings, every line and every step", () => {
    render();
    expect(byLabel("Title")[0].value).toBe("Tomato rice");
    expect(document.querySelector<HTMLInputElement>("input[type=number][min='1']")?.value).toBe("4");
    expect(names()).toEqual(["rice", "onion", "salt"]);
    expect(byLabel("Step 1")[0].value).toBe("Fry the garlic.");
    expect(byLabel("Step 2")[0].value).toBe("Add the rice.");
  });

  it("saves a changed title, amount and step with the version it opened", async () => {
    render();
    act(() => setValue(byLabel("Title")[0], "Better rice"));
    act(() => setValue(byLabel("Quantity")[0] as HTMLInputElement, "2"));
    act(() => setValue(byLabel("Step 2")[0], "Add the rice and water."));

    await save();

    const put = calls.find((call) => call.method === "PUT");
    expect(put?.url).toBe("/api/recipes/r1");
    expect(put?.body).toMatchObject({
      version: recipe.version,
      title: "Better rice",
      base_servings: 4,
      steps: ["Fry the garlic.", "Add the rice and water."],
    });
    expect((put?.body as { ingredient_lines: { quantity: number }[] }).ingredient_lines[0].quantity).toBe(2);
    expect(push).toHaveBeenCalledWith("/recipes/r1?from=%2Fnotebooks%2Fnb1");
  });

  it("adds an ingredient, removes another and moves a step", async () => {
    render();
    act(() => button("Add ingredient")?.click());
    expect(names()).toEqual(["rice", "onion", "salt", ""]);
    act(() => setValue(byLabel("Name")[3], "garlic"));
    act(() => document.querySelectorAll<HTMLButtonElement>("[aria-label=Remove]")[0].click());
    expect(names()).toEqual(["onion", "salt", "garlic"]);

    act(() => document.querySelectorAll<HTMLButtonElement>("[aria-label='Move down']")[
      // the step rows come after the three ingredient rows
      3
    ].click());
    expect([byLabel("Step 1")[0].value, byLabel("Step 2")[0].value]).toEqual([
      "Add the rice.",
      "Fry the garlic.",
    ]);
  });

  it("lists a name change when a name is left, and Undo keeps the typed name", async () => {
    replies.match = [{ status: 200, body: { matches: [{ name: "onions", entry: "onion" }] } }];
    render();

    await leaveName(1, "onions");

    expect(calls.find((call) => call.url.endsWith("/name-matches"))?.body).toEqual({ names: ["onions"] });
    expect(document.querySelector("[data-name-change]")?.textContent).toContain("onions → onion");
    expect(names()[1]).toBe("onion");

    act(() => button("Undo")?.click());
    expect(document.querySelector("[data-name-change]")).toBeNull();
    expect(names()[1]).toBe("onions");
  });

  it("shows a proposal first and does not save until the member presses Save again", async () => {
    replies.match = [{ status: 200, body: { matches: [{ name: "onions", entry: "onion" }] } }];
    render();
    act(() => setValue(byLabel("Name")[1], "onions"));

    await save();

    expect(calls.some((call) => call.method === "PUT")).toBe(false);
    expect(document.querySelector("[data-name-change]")).not.toBeNull();

    await save();
    expect(calls.filter((call) => call.method === "PUT")).toHaveLength(1);
    const body = calls.find((call) => call.method === "PUT")?.body as {
      ingredient_lines: { name: string }[];
    };
    expect(body.ingredient_lines[1].name).toBe("onion");
  });

  it("does not check names the member did not touch", async () => {
    render();
    await save();
    expect(calls.some((call) => call.url.endsWith("/name-matches"))).toBe(false);
  });

  it("names the line to fix on a refused save and keeps the edits", async () => {
    replies.put = [
      {
        status: 422,
        body: { code: "ingredient_line_problem", line_problems: [{ name: "rice", kind: "unit_missing" }] },
      },
    ];
    render();
    act(() => setValue(byLabel("Title")[0], "Kept title"));

    await save();

    expect(document.body.textContent).toContain("Add a unit to rice");
    expect(byLabel("Title")[0].value).toBe("Kept title");
    expect(push).not.toHaveBeenCalled();
  });

  it("tells the member the recipe changed, keeps the edits and offers Reload", async () => {
    replies.put = [{ status: 409, body: { code: "recipe_changed" } }];
    render();
    act(() => setValue(byLabel("Title")[0], "My edit"));

    await save();

    expect(document.body.textContent).toContain("This recipe was changed after you opened it.");
    expect(byLabel("Title")[0].value).toBe("My edit");
    act(() => button("Reload")?.click());
    expect(onReload).toHaveBeenCalledTimes(1);
  });

  it("says plainly when the recipe is gone, read-only, or the save failed", async () => {
    for (const [status, text] of [
      [404, "That recipe is no longer available."],
      [403, "You can only read this recipe."],
      [500, "We couldn't save the recipe."],
    ] as const) {
      replies.put = [{ status, body: {} }];
      render();
      await save();
      expect(document.body.textContent).toContain(text);
      act(() => root.unmount());
      root = createRoot(container);
    }
  });

  it("disables Save while saving, and when a field has an error", async () => {
    release = () => {};
    render();
    await act(async () => button("Save")?.click());
    expect(button("Saving…")?.hasAttribute("disabled")).toBe(true);
    await act(async () => release?.());
    await flush();

    act(() => root.unmount());
    root = createRoot(container);
    release = null;
    render();
    act(() => setValue(byLabel("Title")[0], ""));
    expect(button("Save")?.hasAttribute("disabled")).toBe(true);
  });

  it("asks before leaving with unsaved changes, and not otherwise", () => {
    render();
    act(() => link("Back")?.click());
    expect(document.body.textContent).not.toContain("Leave without saving?");

    act(() => setValue(byLabel("Title")[0], "Changed"));
    const back = link("Cancel");
    const click = new MouseEvent("click", { bubbles: true, cancelable: true });
    act(() => {
      back?.dispatchEvent(click);
    });
    expect(click.defaultPrevented).toBe(true);
    expect(document.body.textContent).toContain("Leave without saving?");
  });
});
