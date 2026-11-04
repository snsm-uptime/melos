/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { NotebookResponse } from "@/lib/notebooksClient";

const api = vi.hoisted(() => ({
  fetchDefaultNotebook: vi.fn(),
  fetchPersonalNotebooks: vi.fn(),
  setDefaultNotebook: vi.fn(),
}));
vi.mock("@/lib/notebooksClient", () => api);

import { DefaultNotebookField } from "./DefaultNotebookField";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

function notebook(id: string, name: string, kind: "personal" | "kitchen" = "personal"): NotebookResponse {
  return {
    id,
    name,
    kind,
    owner_alias: "ana",
    access: "owner",
    is_default: false,
    recipe_count: 0,
    kitchen_id: null,
    kitchen_is_archived: null,
    origin_notebook_name: null,
    is_snapshot: false,
    is_own_capture_notebook: false,
  };
}

const flush = () => act(async () => {
  await Promise.resolve();
  await Promise.resolve();
});

describe("DefaultNotebookField", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    api.fetchDefaultNotebook.mockReset();
    api.fetchPersonalNotebooks.mockReset();
    api.setDefaultNotebook.mockReset();
    api.fetchDefaultNotebook.mockResolvedValue({ ok: true, value: notebook("nb-1", "Home") });
    api.fetchPersonalNotebooks.mockResolvedValue({
      ok: true,
      value: [notebook("nb-1", "Home"), notebook("nb-2", "Work"), notebook("k-1", "Casa", "kitchen")],
    });
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.clearAllMocks();
  });

  it("does not load until it is active", async () => {
    act(() => root.render(<DefaultNotebookField active={false} locale="en" />));
    await flush();
    expect(api.fetchPersonalNotebooks).not.toHaveBeenCalled();
  });

  it("shows the default and only personal notebooks once active", async () => {
    act(() => root.render(<DefaultNotebookField active locale="en" />));
    await flush();
    const trigger = container.querySelector('[role="combobox"]') as HTMLButtonElement;
    expect(trigger.getAttribute("aria-label")).toBe("Default notebook");
    expect(trigger.textContent).toContain("Home");
    expect(trigger.disabled).toBe(false);
  });

  it("saves the chosen notebook as the default", async () => {
    api.setDefaultNotebook.mockResolvedValue({ ok: true, value: notebook("nb-2", "Work") });
    act(() => root.render(<DefaultNotebookField active locale="en" />));
    await flush();
    const trigger = container.querySelector('[role="combobox"]') as HTMLButtonElement;
    act(() => trigger.click());
    const option = Array.from(document.querySelectorAll('[role="option"]')).find(
      (el) => el.textContent === "Work",
    ) as HTMLElement;
    await act(async () => option.click());
    await flush();
    expect(api.setDefaultNotebook).toHaveBeenCalledWith("nb-2");
    expect(trigger.textContent).toContain("Work");
  });

  it("reverts and reports when saving fails", async () => {
    api.setDefaultNotebook.mockResolvedValue({ ok: false, status: 500, code: null });
    act(() => root.render(<DefaultNotebookField active locale="en" />));
    await flush();
    const trigger = container.querySelector('[role="combobox"]') as HTMLButtonElement;
    act(() => trigger.click());
    const option = Array.from(document.querySelectorAll('[role="option"]')).find(
      (el) => el.textContent === "Work",
    ) as HTMLElement;
    await act(async () => option.click());
    await flush();
    expect(trigger.textContent).toContain("Home");
    expect(container.textContent).toContain("Could not save the default notebook.");
  });
});
