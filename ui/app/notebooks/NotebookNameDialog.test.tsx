/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NotebookResponse, NotebookResult } from "@/lib/notebooksClient";

import { NotebookNameDialog } from "./NotebookNameDialog";

const replace = vi.fn();
const router = { replace };
vi.mock("next/navigation", () => ({ useRouter: () => router }));

const failure = (status: number, code: string | null): NotebookResult<NotebookResponse> => ({
  ok: false,
  status,
  code,
});

describe("NotebookNameDialog", () => {
  let container: HTMLDivElement;
  let root: Root;
  const onSaved = vi.fn();
  const onClose = vi.fn();

  beforeEach(() => {
    replace.mockReset();
    onSaved.mockReset();
    onClose.mockReset();
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  async function renderWith(
    submit: (name: string) => Promise<NotebookResult<NotebookResponse>>,
    locale: "en" | "es" = "en",
  ) {
    await act(async () => {
      root.render(
        <NotebookNameDialog
          title="Rename notebook"
          confirmLabel="Save"
          initialName="Soups"
          failedMessage="Could not rename the notebook. Try again."
          locale={locale}
          submit={submit}
          onSaved={onSaved}
          onClose={onClose}
          goneHref="/kitchens/k1/notebooks"
          returnTo="/notebooks/nb-1"
        />,
      );
    });
  }

  const input = () => container.querySelector('input[type="text"]') as HTMLInputElement;
  const alert = () => container.querySelector('[role="alert"]')?.textContent;
  const button = (name: string) =>
    Array.from(container.querySelectorAll("button")).find(
      (el) => el.textContent === name,
    ) as HTMLButtonElement;

  async function click(el: Element) {
    await act(async () => {
      el.dispatchEvent(new MouseEvent("click", { bubbles: true }));
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }

  async function type(value: string) {
    await act(async () => {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!.call(input(), value);
      input().dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  it("starts from the current name and sends the trimmed one", async () => {
    const notebook = { id: "nb-1", name: "Winter soups" } as NotebookResponse;
    const submit = vi.fn(async () => ({ ok: true as const, value: notebook }));
    await renderWith(submit);
    expect(input().value).toBe("Soups");
    expect(input().maxLength).toBe(200);
    expect(document.activeElement).toBe(input());

    await type("  Winter soups ");
    await click(button("Save"));

    expect(submit).toHaveBeenCalledWith("Winter soups");
    expect(onSaved).toHaveBeenCalledWith(notebook);
  });

  it("asks for a name, keeps the spaces and sends nothing when blank", async () => {
    const submit = vi.fn(async () => failure(500, null));
    await renderWith(submit);
    await type("   ");
    await click(button("Save"));
    expect(submit).not.toHaveBeenCalled();
    expect(alert()).toBe("Enter a name for the notebook.");
    expect(input().value).toBe("   ");
  });

  it.each([
    ["invalid_notebook_name", 422, "Enter a name for the notebook."],
    ["kitchen_archived", 403, "This kitchen is archived, so its notebooks can't be changed."],
    [null, 500, "Could not rename the notebook. Try again."],
  ])("stays open with the text kept on %s", async (code, status, message) => {
    await renderWith(async () => failure(status, code));
    await type("Winter soups");
    await click(button("Save"));
    expect(alert()).toBe(message);
    expect(input().value).toBe("Winter soups");
    expect(onClose).not.toHaveBeenCalled();
  });

  it("says the notebook is gone, and closing goes to the gone address", async () => {
    await renderWith(async () => failure(404, "notebook_not_found"));
    await click(button("Save"));
    expect(alert()).toBe("This notebook no longer exists.");
    expect(button("Save")).toBeUndefined();
    await click(button("Close"));
    expect(replace).toHaveBeenCalledWith("/kitchens/k1/notebooks");
  });

  it("says the kitchen is gone, and closing goes to the kitchens", async () => {
    await renderWith(async () => failure(404, "kitchen_not_found"));
    await click(button("Save"));
    expect(alert()).toBe("This kitchen is no longer available.");
    await click(button("Close"));
    expect(replace).toHaveBeenCalledWith("/kitchens");
  });

  it("sends a person with no alias to choose one and back", async () => {
    await renderWith(async () => failure(403, "alias_required"));
    await click(button("Save"));
    expect(replace).toHaveBeenCalledWith("/alias?returnTo=%2Fnotebooks%2Fnb-1");
  });

  it("closes on Cancel", async () => {
    await renderWith(async () => failure(500, null));
    await click(button("Cancel"));
    expect(onClose).toHaveBeenCalled();
  });

  it("speaks Spanish", async () => {
    await renderWith(async () => failure(404, "notebook_not_found"), "es");
    await click(button("Save"));
    expect(alert()).toBe("Este cuaderno ya no existe.");
  });
});
