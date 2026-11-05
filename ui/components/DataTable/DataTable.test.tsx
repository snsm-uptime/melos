/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { tableMessages } from "@/lib/i18n/table";

import { DataTable } from "./DataTable";
import type { TableSchema } from "./types";

/** An invented row type: the table needs only a schema to handle it (spec 066 US3). */
type Thing = { name: string; size: number; seen: string | null };

const schema: TableSchema<Thing> = {
  search: true,
  rowKey: (row) => row.name,
  columns: [
    { key: "name", label: "Name", sort: "text", searchable: true },
    { key: "size", label: "Size", sort: "number" },
    { key: "seen", label: "Seen", sort: "date", cell: (r) => r.seen ?? "—" },
    { key: "note", label: "Note", sort: false, cell: () => "x" },
  ],
};

const ROWS: Thing[] = [
  { name: "Sopa de maíz", size: 10, seen: "2026-02-01" },
  { name: "pan", size: 9, seen: null },
  { name: "Arroz", size: 10, seen: "2026-01-01" },
];

describe("DataTable", () => {
  let container: HTMLDivElement;
  let root: Root;
  const fetchSpy = vi.fn();

  beforeEach(() => {
    fetchSpy.mockReset();
    vi.stubGlobal("fetch", fetchSpy);
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  function render(rows: Thing[] = ROWS, s: TableSchema<Thing> = schema) {
    act(() =>
      root.render(
        <DataTable
          schema={s}
          rows={rows}
          locale="en"
          labels={tableMessages.en}
          empty="Nothing here yet."
        />,
      ),
    );
  }

  const th = (label: string) =>
    Array.from(container.querySelectorAll("th")).find((el) =>
      el.textContent?.startsWith(label),
    )!;
  const heading = (label: string) => th(label).querySelector("button")!;
  const click = (label: string) => act(() => heading(label).click());
  const firstColumn = () =>
    Array.from(container.querySelectorAll("tbody tr td:first-child")).map(
      (td) => td.textContent,
    );
  const clearButton = () =>
    Array.from(container.querySelectorAll("button")).find(
      (b) => b.textContent === "Clear sort",
    );
  const input = () => container.querySelector<HTMLInputElement>("input")!;

  function type(text: string) {
    const setter = Object.getOwnPropertyDescriptor(
      HTMLInputElement.prototype,
      "value",
    )!.set!;
    act(() => {
      setter.call(input(), text);
      input().dispatchEvent(new Event("input", { bubbles: true }));
    });
  }

  it("renders a schema over an invented row type in the loaded order", () => {
    render();
    expect(firstColumn()).toEqual(["Sopa de maíz", "pan", "Arroz"]);
  });

  it("cycles a heading asc → desc → off, with aria-sort", () => {
    render();
    expect(th("Name").hasAttribute("aria-sort")).toBe(false);
    click("Name");
    expect(th("Name").getAttribute("aria-sort")).toBe("ascending");
    expect(firstColumn()).toEqual(["Arroz", "pan", "Sopa de maíz"]);
    click("Name");
    expect(th("Name").getAttribute("aria-sort")).toBe("descending");
    expect(firstColumn()).toEqual(["Sopa de maíz", "pan", "Arroz"]);
    click("Name");
    expect(th("Name").hasAttribute("aria-sort")).toBe(false);
    expect(firstColumn()).toEqual(["Sopa de maíz", "pan", "Arroz"]);
  });

  it("adds a second level and shows both level numbers", () => {
    render();
    click("Size");
    click("Name");
    expect(firstColumn()).toEqual(["pan", "Arroz", "Sopa de maíz"]);
    expect(heading("Size").getAttribute("aria-label")).toBe(
      "Size, sort level 1, ascending",
    );
    expect(heading("Name").getAttribute("aria-label")).toBe(
      "Name, sort level 2, ascending",
    );
    expect(heading("Size").textContent).toContain("1");
    expect(heading("Name").textContent).toContain("2");
  });

  it("shows Clear sort only while sorted, and it restores the loaded order", () => {
    render();
    expect(clearButton()).toBeUndefined();
    click("Size");
    act(() => clearButton()!.click());
    expect(clearButton()).toBeUndefined();
    expect(firstColumn()).toEqual(["Sopa de maíz", "pan", "Arroz"]);
  });

  it("puts empty dates last both ways", () => {
    render();
    click("Seen");
    expect(firstColumn().at(-1)).toBe("pan");
    click("Seen");
    expect(firstColumn().at(-1)).toBe("pan");
  });

  it("renders a column with sort: false as plain text", () => {
    render();
    expect(th("Note").querySelector("button")).toBeNull();
    expect(th("Note").hasAttribute("aria-sort")).toBe(false);
  });

  it("sorts with Enter on a focused heading (a native button)", () => {
    render();
    expect(heading("Size").tagName).toBe("BUTTON");
    expect(heading("Size").getAttribute("type")).toBe("button");
  });

  it("never fetches and never mutates rows", () => {
    const rows = [...ROWS];
    render(rows);
    click("Name");
    type("pan");
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(rows).toEqual(ROWS);
  });

  it("shows the empty text for no rows, with no search bar", () => {
    render([]);
    expect(container.textContent).toBe("Nothing here yet.");
    expect(container.querySelector("input")).toBeNull();
  });

  it("filters as the admin types, ignoring accents, and sorts the filtered rows", () => {
    render();
    expect(
      container.querySelector(`label[for="${input().id}"]`)?.textContent,
    ).toBe("Search this table");
    type("A");
    click("Name");
    expect(firstColumn()).toEqual(["Arroz", "pan", "Sopa de maíz"]);
    type("MAIZ");
    expect(firstColumn()).toEqual(["Sopa de maíz"]);
    expect(container.querySelector('[role="status"]')?.textContent).toBe(
      "1 row shown",
    );
  });

  it("says nothing matches, keeps the input, and clearing restores every row", () => {
    render();
    type("zzz");
    expect(container.querySelector("table")).toBeNull();
    expect(container.textContent).toContain("Nothing matches your search.");
    expect(input().disabled).toBe(false);
    type("");
    expect(firstColumn()).toHaveLength(3);
  });

  it("has no search bar when the schema turns search off", () => {
    render(ROWS, { ...schema, search: false });
    expect(container.querySelector("input")).toBeNull();
  });
});
