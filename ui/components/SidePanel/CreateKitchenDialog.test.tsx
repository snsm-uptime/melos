/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const createKitchen = vi.fn();
vi.mock("@/app/kitchens/kitchensClient", () => ({
  createKitchen: (...args: unknown[]) => createKitchen(...args),
}));

import { CreateKitchenDialog } from "./CreateKitchenDialog";

describe("CreateKitchenDialog", () => {
  let host: HTMLDivElement;
  let root: Root;
  const onOpenChange = vi.fn();
  const onCreated = vi.fn();

  beforeEach(async () => {
    vi.clearAllMocks();
    (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
    await act(async () => {
      root.render(
        <CreateKitchenDialog open locale="en" onOpenChange={onOpenChange} onCreated={onCreated} />,
      );
    });
  });
  afterEach(() => {
    act(() => root.unmount());
    host.remove();
  });

  const submit = () =>
    [...document.querySelectorAll("button")].find((b) => b.textContent === "Create kitchen")!;

  function type(value: string) {
    const input = document.querySelector("input")!;
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
    setter.call(input, value);
    input.dispatchEvent(new Event("input", { bubbles: true }));
  }

  it("refuses a blank name without calling the api", async () => {
    await act(async () => submit().click());
    expect(document.querySelector("[role=alert]")?.textContent).toBe("Enter a kitchen name.");
    expect(createKitchen).not.toHaveBeenCalled();
  });

  it("creates and closes", async () => {
    createKitchen.mockResolvedValue({ ok: true, kitchen: {} });
    await act(async () => type("Beach house"));
    await act(async () => submit().click());
    expect(createKitchen.mock.calls[0][0]).toBe("Beach house");
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(onCreated).toHaveBeenCalled();
  });

  it("keeps the dialog open and shows an api error", async () => {
    createKitchen.mockResolvedValue({ ok: false, error: "Nope" });
    await act(async () => type("Beach house"));
    await act(async () => submit().click());
    expect(document.querySelector("[role=alert]")?.textContent).toBe("Nope");
    expect(onOpenChange).not.toHaveBeenCalled();
  });
});
