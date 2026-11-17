/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { NotebookPicker, type NotebookPickerOption } from "./NotebookPicker";
import { notebookChoices, notebookPicker } from "./testHelpers";

let container: HTMLDivElement;
let root: Root;

function render(notebooks: NotebookPickerOption[]) {
  act(() => {
    root.render(
      <NotebookPicker
        value={notebooks[0].id}
        notebooks={notebooks}
        onChange={() => {}}
        label="Notebook"
        locale="en"
      />,
    );
  });
}

function type(text: string) {
  const search = document.querySelector("input") as HTMLInputElement;
  act(() => {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(search, text);
    search.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
});

describe("NotebookPicker (spec 076)", () => {
  it("shows the detail after the name, and finds a notebook by it", () => {
    render([
      { id: "p1", name: "Weekend", detail: "Personal" },
      { id: "k1", name: "Dinners", detail: "Casa", dividerBefore: true },
    ]);
    expect(notebookChoices()).toEqual(["Weekend · Personal", "Dinners · Casa"]);

    act(() => notebookPicker()!.click());
    type("Casa");
    const found = Array.from(document.querySelectorAll('[role="option"]')).map((o) => o.textContent);
    expect(found).toEqual(["Dinners · Casa"]);
  });

  it("shows the name alone without a detail", () => {
    render([
      { id: "p1", name: "Weekend" },
      { id: "p2", name: "Dinners" },
    ]);
    expect(notebookChoices()).toEqual(["Weekend", "Dinners"]);
  });

  it("draws a divider above a row that starts a group", () => {
    render([
      { id: "p1", name: "Weekend", detail: "Personal" },
      { id: "k1", name: "Dinners", detail: "Casa", dividerBefore: true },
    ]);
    act(() => notebookPicker()!.click());
    const rows = Array.from(document.querySelectorAll('[role="listbox"] > li')).map((li) =>
      li.getAttribute("role"),
    );
    expect(rows).toEqual(["option", "separator", "option"]);
  });
});
