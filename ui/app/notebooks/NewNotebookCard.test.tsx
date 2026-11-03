/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NewNotebookCard } from "./NewNotebookCard";

const push = vi.fn();
const replace = vi.fn();
const router = { push, replace };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

describe("NewNotebookCard", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    push.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    act(() => root.render(<NewNotebookCard locale="en" />));
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  function reply(status: number, body: unknown) {
    const fetchMock = vi.fn(async () => ({
      ok: status < 300,
      status,
      json: async () => body,
    }));
    vi.stubGlobal("fetch", fetchMock);
    return fetchMock;
  }

  const button = (name: string) =>
    Array.from(container.querySelectorAll("button")).find(
      (el) => el.textContent === name || el.getAttribute("aria-label") === name,
    ) as HTMLButtonElement;

  async function click(el: Element) {
    await act(async () => {
      el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }

  async function open(value: string) {
    await click(button("New notebook"));
    const input = container.querySelector('input[type="text"]') as HTMLInputElement;
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input, value);
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  it("creates the notebook from the name and opens it", async () => {
    const fetchMock = reply(201, { id: "nb-9", name: "Postres" });
    await open("  Postres ");
    await click(button("Create"));
    const init = (fetchMock.mock.calls[0] as unknown as [string, RequestInit])[1];
    expect(JSON.parse(init.body as string)).toEqual({ name: "Postres" });
    expect(push).toHaveBeenCalledWith("/notebooks/nb-9");
  });

  it("creates with Enter", async () => {
    reply(201, { id: "nb-9", name: "Postres" });
    await open("Postres");
    await act(async () => {
      container
        .querySelector("form")!
        .dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(push).toHaveBeenCalledWith("/notebooks/nb-9");
  });

  it("asks for a name and calls nothing when it is blank", async () => {
    const fetchMock = reply(201, {});
    await open("   ");
    await click(button("Create"));
    expect(fetchMock).not.toHaveBeenCalled();
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Enter a name");
  });

  it("keeps the name and says so when creating fails", async () => {
    reply(500, {});
    await open("Postres");
    await click(button("Create"));
    expect(push).not.toHaveBeenCalled();
    expect(container.querySelector('[role="alert"]')?.textContent).toContain("Could not create");
    expect((container.querySelector('input[type="text"]') as HTMLInputElement).value).toBe(
      "Postres",
    );
  });

  it("clears the name when cancelled", async () => {
    await open("Postres");
    await click(button("Cancel"));
    expect(container.querySelector('[role="dialog"]')).toBeNull();
    await click(button("New notebook"));
    expect((container.querySelector('input[type="text"]') as HTMLInputElement).value).toBe("");
  });

  describe("in a kitchen", () => {
    beforeEach(() => {
      replace.mockReset();
      act(() => root.render(<NewNotebookCard locale="en" kitchenId="k1" />));
    });

    it("adds to the kitchen and opens the notebook with the way back to its list", async () => {
      const fetchMock = reply(201, { id: "nb-9", name: "Holidays" });
      await open("Holidays");
      await click(button("Create"));
      expect((fetchMock.mock.calls[0] as unknown as [string])[0]).toBe(
        "/api/notebooks/kitchens/k1",
      );
      expect(push).toHaveBeenCalledWith(
        `/notebooks/nb-9?from=${encodeURIComponent("/kitchens/k1/notebooks")}`,
      );
    });

    it("says the kitchen is gone, and closing goes to the kitchens", async () => {
      reply(404, { code: "kitchen_not_found" });
      await open("Holidays");
      await click(button("Create"));
      expect(container.querySelector('[role="alert"]')?.textContent).toBe(
        "This kitchen is no longer available.",
      );
      await click(button("Close"));
      expect(replace).toHaveBeenCalledWith("/kitchens");
    });
  });
});
