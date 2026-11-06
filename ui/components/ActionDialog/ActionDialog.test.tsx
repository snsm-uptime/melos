/** @vitest-environment jsdom */

import { act, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { ActionDialog } from "./ActionDialog";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

/** A dialog with a ✕, and a confirmation that can open over it. */
function Nested() {
  const [outer, setOuter] = useState(true);
  const [inner, setInner] = useState(false);
  return (
    <ActionDialog open={outer} title="Places" closeLabel="Close" onOpenChange={setOuter}>
      <button type="button" onClick={() => setInner(true)}>
        Delete
      </button>
      <ActionDialog
        open={inner}
        title="Delete it?"
        confirmLabel="Delete"
        cancelLabel="Cancel"
        onOpenChange={setInner}
      >
        Sure?
      </ActionDialog>
    </ActionDialog>
  );
}

describe("ActionDialog", () => {
  let host: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
    act(() => root.render(<Nested />));
  });
  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });

  const dialogs = () => Array.from(document.querySelectorAll('[role="dialog"]'));
  const escape = () =>
    act(() => {
      document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });

  it("names itself by its title and closes with the ✕", () => {
    const [dialog] = dialogs();
    const title = document.getElementById(dialog.getAttribute("aria-labelledby")!);
    expect(title?.textContent).toBe("Places");
    act(() => document.querySelector<HTMLButtonElement>('button[aria-label="Close"]')!.click());
    expect(dialogs()).toHaveLength(0);
  });

  it("closes only the dialog on top when Escape is pressed", () => {
    act(() =>
      Array.from(document.querySelectorAll("button"))
        .find((b) => b.textContent === "Delete")!
        .click(),
    );
    expect(dialogs()).toHaveLength(2);
    escape();
    expect(dialogs().map((d) => d.querySelector("h2")?.textContent)).toEqual(["Places"]);
    escape();
    expect(dialogs()).toHaveLength(0);
  });
});
