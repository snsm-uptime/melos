/** @vitest-environment jsdom */

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { IconButton } from "@/components/IconButton";

vi.mock("@/components/MenuSurface/MenuSurface.module.scss", () => ({
  default: new Proxy(
    {},
    {
      get: (_t, prop) => String(prop),
    },
  ),
}));

vi.mock("./IconButtonPopup.module.scss", () => ({
  default: new Proxy(
    {},
    {
      get: (_t, prop) => String(prop),
    },
  ),
}));

vi.mock("@/components/IconButton/IconButton.module.scss", () => ({
  default: new Proxy(
    {},
    {
      get: (_t, prop) => String(prop),
    },
  ),
}));

import { IconButtonPopup, IconButtonPopupItem, IconButtonPopupLinkItem } from "./IconButtonPopup";

const here = dirname(fileURLToPath(import.meta.url));

function dispatchPointerDown(target: EventTarget) {
  target.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true }));
}

describe("IconButtonPopup", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    container.remove();
  });

  it("opens on IconButton click and wires menu aria onto that button", async () => {
    await act(async () => {
      root.render(
        <IconButtonPopup button={<IconButton icon={<span />} label="Options" />}>
          <IconButtonPopupItem>Invite</IconButtonPopupItem>
        </IconButtonPopup>,
      );
    });

    const trigger = container.querySelector("button") as HTMLButtonElement;
    expect(trigger.getAttribute("aria-label")).toBe("Options");
    expect(trigger.getAttribute("aria-haspopup")).toBe("menu");
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(container.querySelector('[role="menu"]')).toBeNull();

    await act(async () => {
      trigger.click();
    });

    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(trigger.getAttribute("aria-controls")).toBeTruthy();
    expect(container.querySelector('[role="menu"]')?.textContent).toContain("Invite");
    expect(container.firstElementChild?.className).toContain("open");
  });

  it("does not close when clicking non-item content inside the popup", async () => {
    await act(async () => {
      root.render(
        <IconButtonPopup button={<IconButton icon={<span />} label="Options" />}>
          <p>Keep me</p>
          <IconButtonPopupItem>Invite</IconButtonPopupItem>
        </IconButtonPopup>,
      );
    });

    const trigger = container.querySelector("button") as HTMLButtonElement;
    await act(async () => {
      trigger.click();
    });

    const note = Array.from(container.querySelectorAll("p")).find(
      (el) => el.textContent === "Keep me",
    ) as HTMLParagraphElement;
    await act(async () => {
      note.click();
    });

    expect(container.querySelector('[role="menu"]')).not.toBeNull();
    expect(container.textContent).toContain("Keep me");
  });

  it("closes on an item click without blocking that item's handler", async () => {
    const onInvite = vi.fn();
    await act(async () => {
      root.render(
        <IconButtonPopup button={<IconButton icon={<span />} label="Options" />}>
          <IconButtonPopupItem onClick={onInvite}>Invite</IconButtonPopupItem>
        </IconButtonPopup>,
      );
    });

    const trigger = container.querySelector("button") as HTMLButtonElement;
    await act(async () => {
      trigger.click();
    });

    const item = Array.from(container.querySelectorAll('[role="menuitem"]')).find(
      (el) => el.textContent === "Invite",
    ) as HTMLButtonElement;
    await act(async () => {
      item.click();
    });

    expect(onInvite).toHaveBeenCalledTimes(1);
    expect(container.querySelector('[role="menu"]')).toBeNull();
  });

  it("closes on a pointerdown outside the popup", async () => {
    await act(async () => {
      root.render(
        <IconButtonPopup button={<IconButton icon={<span />} label="Options" />}>
          <IconButtonPopupItem>Invite</IconButtonPopupItem>
        </IconButtonPopup>,
      );
    });

    const trigger = container.querySelector("button") as HTMLButtonElement;
    await act(async () => {
      trigger.click();
    });
    expect(container.querySelector('[role="menu"]')).not.toBeNull();

    await act(async () => {
      dispatchPointerDown(document.body);
    });

    expect(container.querySelector('[role="menu"]')).toBeNull();
  });

  it("keeps the popup open when an item opts into stayOpen", async () => {
    const onDelete = vi.fn();
    await act(async () => {
      root.render(
        <IconButtonPopup button={<IconButton icon={<span />} label="Options" />}>
          <IconButtonPopupItem stayOpen onClick={onDelete}>
            Delete
          </IconButtonPopupItem>
        </IconButtonPopup>,
      );
    });

    const trigger = container.querySelector("button") as HTMLButtonElement;
    await act(async () => {
      trigger.click();
    });

    const item = Array.from(container.querySelectorAll('[role="menuitem"]')).find(
      (el) => el.textContent === "Delete",
    ) as HTMLButtonElement;
    await act(async () => {
      item.click();
    });

    expect(onDelete).toHaveBeenCalledTimes(1);
    expect(container.querySelector('[role="menu"]')).not.toBeNull();
  });

  it("toggles closed when the IconButton is clicked while open", async () => {
    await act(async () => {
      root.render(
        <IconButtonPopup button={<IconButton icon={<span />} label="Options" />}>
          <IconButtonPopupItem>Invite</IconButtonPopupItem>
        </IconButtonPopup>,
      );
    });

    const trigger = container.querySelector("button") as HTMLButtonElement;
    await act(async () => {
      trigger.click();
    });
    expect(container.querySelector('[role="menu"]')).not.toBeNull();

    await act(async () => {
      trigger.click();
    });
    expect(container.querySelector('[role="menu"]')).toBeNull();
  });
});

describe("IconButtonPopup.module.scss", () => {
  const css = readFileSync(join(here, "IconButtonPopup.module.scss"), "utf8");

  it("anchors the panel below the trigger with the lists menu chrome", () => {
    expect(css).toContain("top: calc(100% + 0.35rem);");
    expect(css).toContain("min-width: var(--icon-button-popup-min-width, 11rem);");
    expect(css).toContain("animation: slideDown 0.15s ease-out;");
    expect(css).toContain(".root.open");
    expect(css).toContain("z-index: 5;");
    expect(css).not.toContain("background: var(--surface);");
  });

  it("puts each item's icon before its label in the fixed-size icon slot", () => {
    const container = document.createElement("div");
    const root = createRoot(container);
    act(() => {
      root.render(
        <IconButtonPopup open button={<IconButton label="More" icon={<span />} />}>
          <IconButtonPopupItem icon={<svg data-testid="edit" />}>Edit</IconButtonPopupItem>
          <IconButtonPopupLinkItem href="/x" icon={<svg data-testid="go" />}>
            Go
          </IconButtonPopupLinkItem>
          <IconButtonPopupItem>Plain</IconButtonPopupItem>
        </IconButtonPopup>,
      );
    });
    const items = Array.from(container.querySelectorAll("[role=menuitem]"));
    const pairs: [Element, string][] = [
      [items[0], "Edit"],
      [items[1], "Go"],
    ];
    for (const [item, label] of pairs) {
      const [icon, text] = Array.from(item.children);
      expect(icon.className).toBe("itemIcon");
      expect(icon.querySelector("svg")).not.toBeNull();
      expect(text.textContent).toBe(label);
    }
    expect(items[1].getAttribute("href")).toBe("/x");
    expect(items[2].querySelector(".itemIcon")).toBeNull();
    act(() => root.unmount());
  });

  it("sizes the icon slot like the chrome icons and keeps labels on one line", () => {
    const css = readFileSync(join(here, "IconButtonPopup.module.scss"), "utf8");
    expect(css).toMatch(/\.itemIcon \{[^}]*flex-shrink: 0;[^}]*width: 1\.5rem;[^}]*height: 1\.5rem;/);
    expect(css).toMatch(/\.itemLayout \{[^}]*white-space: nowrap;/);
  });
});
