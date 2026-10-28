/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { DeleteRecipeDialog } from "./DeleteRecipeDialog";

const onDeleted = vi.fn();
const onOpenChange = vi.fn();

function stubFetch(status: number | Error) {
  let finish: () => void = () => {};
  const gate = new Promise<void>((resolve) => (finish = resolve));
  const mock = vi.fn(async () => {
    await gate;
    if (status instanceof Error) throw status;
    return new Response(status === 204 ? null : JSON.stringify({ code: "x" }), { status });
  });
  vi.stubGlobal("fetch", mock);
  return { mock, finish };
}

describe("DeleteRecipeDialog", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    onDeleted.mockReset();
    onOpenChange.mockReset();
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  function render(open = true) {
    act(() => {
      root.render(
        <DeleteRecipeDialog
          open={open}
          onOpenChange={onOpenChange}
          recipeId="r1"
          title="Tomato rice"
          locale="en"
          onDeleted={onDeleted}
        />,
      );
    });
  }

  const button = (label: string) =>
    Array.from(document.querySelectorAll("button")).find((b) => b.textContent === label);

  async function settle(finish: () => void) {
    await act(async () => {
      finish();
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }

  it("names the recipe and sends nothing until the member confirms", () => {
    const { mock } = stubFetch(204);
    render();
    expect(document.body.textContent).toContain("Delete “Tomato rice”?");
    expect(document.body.textContent).toContain("This can't be undone.");
    expect(mock).not.toHaveBeenCalled();
  });

  it("closes on Cancel without a request", () => {
    const { mock } = stubFetch(204);
    render();
    act(() => button("Cancel")?.click());
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(mock).not.toHaveBeenCalled();
    expect(onDeleted).not.toHaveBeenCalled();
  });

  it("sends one request even when Delete is pressed twice, then leaves", async () => {
    const { mock, finish } = stubFetch(204);
    render();
    act(() => {
      button("Delete")?.click();
      button("Deleting…")?.click();
      button("Delete")?.click();
    });
    await settle(finish);
    expect(mock).toHaveBeenCalledTimes(1);
    expect((mock.mock.calls[0] as unknown as [string, RequestInit])[1].method).toBe("DELETE");
    expect(onDeleted).toHaveBeenCalledTimes(1);
  });

  it("treats a recipe already deleted elsewhere as done", async () => {
    const { finish } = stubFetch(404);
    render();
    act(() => button("Delete")?.click());
    await settle(finish);
    expect(onDeleted).toHaveBeenCalledTimes(1);
  });

  it("stays open with a plain message when the member can only read", async () => {
    const { finish } = stubFetch(403);
    render();
    act(() => button("Delete")?.click());
    await settle(finish);
    expect(onDeleted).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain("You can only read this recipe.");
  });

  it("stays open with a retry message when the request fails", async () => {
    const { finish } = stubFetch(new Error("down"));
    render();
    act(() => button("Delete")?.click());
    await settle(finish);
    expect(onDeleted).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain("The recipe wasn't deleted. Try again.");
    expect(button("Delete")).toBeDefined();
  });
});
