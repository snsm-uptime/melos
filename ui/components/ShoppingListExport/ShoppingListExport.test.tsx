/** @vitest-environment jsdom */

import { act } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { client } = vi.hoisted(() => ({
  client: { fetchExportText: vi.fn(), fetchExportPdf: vi.fn() },
}));
vi.mock("./exportText", async (importOriginal) => ({
  ...(await importOriginal<typeof import("./exportText")>()),
  fetchExportText: client.fetchExportText,
  fetchExportPdf: client.fetchExportPdf,
}));

import { mount } from "@/components/Cart/testRoot";

import { ShoppingListExport } from "./ShoppingListExport";

const LIST = "## Shopping list (2026-11-17)\n\n- rice — 2 cup (Rice)\n";
const EMPTY = "## Shopping list (2026-11-17)\n\nNo items\n";

async function settle() {
  await act(async () => {
    await Promise.resolve();
  });
}

function button(container: HTMLElement, label: string): HTMLButtonElement {
  const found = [...container.querySelectorAll("button")].find(
    (b) => b.textContent === label,
  );
  if (!found) throw new Error(`no button ${label}`);
  return found;
}

describe("ShoppingListExport", () => {
  let view: ReturnType<typeof mount>;
  const writeText = vi.fn().mockResolvedValue(undefined);

  beforeEach(() => {
    view = mount();
    client.fetchExportText.mockReset();
    client.fetchExportPdf.mockReset();
    writeText.mockClear();
    vi.stubGlobal("navigator", { clipboard: { writeText } });
    vi.stubGlobal(
      "URL",
      Object.assign(URL, {
        createObjectURL: vi.fn(() => "blob:x"),
        revokeObjectURL: vi.fn(),
      }),
    );
  });

  afterEach(() => {
    view.unmount();
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("loads the Markdown into the copy box", async () => {
    client.fetchExportText.mockResolvedValue({ ok: true, value: LIST });
    view.render(<ShoppingListExport kitchenId="k1" listId="l1" />);
    await settle();
    const box = view.container.querySelector("textarea") as HTMLTextAreaElement;
    expect(box.value).toBe(LIST);
    expect(box.readOnly).toBe(true);
  });

  it("copies the exact text and shows the confirmation", async () => {
    client.fetchExportText.mockResolvedValue({ ok: true, value: LIST });
    view.render(<ShoppingListExport kitchenId="k1" listId="l1" />);
    await settle();
    await act(async () => {
      button(view.container, "Copy").click();
      await Promise.resolve();
    });
    expect(writeText).toHaveBeenCalledWith(LIST);
    expect(
      view.container.querySelector('[role="status"]')?.textContent,
    ).toContain("Copied");
  });

  it("disables both actions and shows the hint for an empty list", async () => {
    client.fetchExportText.mockResolvedValue({ ok: true, value: EMPTY });
    view.render(<ShoppingListExport kitchenId="k1" listId="l1" />);
    await settle();
    expect(button(view.container, "Copy").disabled).toBe(true);
    expect(button(view.container, "Download PDF").disabled).toBe(true);
    expect(view.container.textContent).toContain(
      "Add recipes or items to the list first.",
    );
  });

  it("keeps the copy box and Copy usable when the PDF fails", async () => {
    client.fetchExportText.mockResolvedValue({ ok: true, value: LIST });
    client.fetchExportPdf.mockResolvedValue({
      ok: false,
      status: 500,
      code: null,
    });
    view.render(<ShoppingListExport kitchenId="k1" listId="l1" />);
    await settle();
    await act(async () => {
      button(view.container, "Download PDF").click();
      await Promise.resolve();
    });
    await settle();
    expect(
      view.container.querySelector('[role="alert"]')?.textContent,
    ).toContain("The PDF could not be made");
    expect(URL.createObjectURL).not.toHaveBeenCalled();
    expect(button(view.container, "Copy").disabled).toBe(false);
    expect(
      (view.container.querySelector("textarea") as HTMLTextAreaElement).value,
    ).toBe(LIST);
  });

  it("saves the PDF through a temporary object URL on success", async () => {
    client.fetchExportText.mockResolvedValue({ ok: true, value: LIST });
    client.fetchExportPdf.mockResolvedValue({
      ok: true,
      value: {
        blob: new Blob(["%PDF"]),
        fileName: "shopping-list-2026-11-17.pdf",
      },
    });
    view.render(<ShoppingListExport kitchenId="k1" listId="l1" />);
    await settle();
    await act(async () => {
      button(view.container, "Download PDF").click();
      await Promise.resolve();
    });
    await settle();
    expect(URL.createObjectURL).toHaveBeenCalledTimes(1);
  });

  it("offers a retry when the text cannot load", async () => {
    client.fetchExportText.mockResolvedValueOnce({
      ok: false,
      status: 500,
      code: null,
    });
    view.render(<ShoppingListExport kitchenId="k1" listId="l1" />);
    await settle();
    expect(
      view.container.querySelector('[role="alert"]')?.textContent,
    ).toContain("Could not load the export");
    client.fetchExportText.mockResolvedValueOnce({ ok: true, value: LIST });
    await act(async () => {
      button(view.container, "Try again").click();
    });
    await settle();
    expect(
      (view.container.querySelector("textarea") as HTMLTextAreaElement).value,
    ).toBe(LIST);
  });
});
