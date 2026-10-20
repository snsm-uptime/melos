/**
 * @vitest-environment jsdom
 */
import { act } from "react";
import type { ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { Hint } from "./Hint";
import { PrimaryButton } from "./PrimaryButton";
import { SectionLabel } from "./SectionLabel";
import { SoftLedgerRadio } from "./Radio";
import { SoftLedgerSelect } from "./Select";
import { TabBar } from "./TabBar";

vi.mock("next/link", () => ({
  default: ({
    href,
    children,
    className,
    ...rest
  }: {
    href: string;
    children: ReactNode;
    className?: string;
    "aria-current"?: "page" | undefined;
  }) => (
    <a href={href} className={className} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/components/IconButton/IconButton.module.scss", () => ({
  default: new Proxy(
    {},
    {
      get: (_target, key) => (typeof key === "string" ? key : "mod"),
    },
  ),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: vi.fn() }),
}));

describe("Soft-Ledger primitives", () => {
  let host: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    host = document.createElement("div");
    document.body.appendChild(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => {
      root.unmount();
    });
    host.remove();
    vi.unstubAllGlobals();
  });

  it("renders Hint and SectionLabel", () => {
    act(() => {
      root.render(
        <>
          <Hint>Shared recipes will land here.</Hint>
          <SectionLabel>Members</SectionLabel>
        </>,
      );
    });
    expect(host.textContent).toContain("Shared recipes will land here.");
    expect(host.querySelector("h2")?.textContent).toBe("Members");
  });

  it("TabBar renders one link per item + aria-current on the active tab", () => {
    function DummyIcon(props: { className?: string }) {
      return <svg {...props} />;
    }
    act(() => {
      root.render(
        <TabBar
          items={[
            { key: "home", href: "/home", label: "Home", Icon: DummyIcon },
            { key: "upload", href: "/upload", label: "Upload", Icon: DummyIcon },
            { key: "budgets", href: "/budgets", label: "Budgets", Icon: DummyIcon },
            { key: "account", href: "/account", label: "Account", Icon: DummyIcon },
          ]}
          ariaLabel="Primary"
          active="home"
        />,
      );
    });
    const nav = host.querySelector("nav");
    expect(nav?.getAttribute("aria-label")).toBe("Primary");
    expect(nav?.className).toContain("justify-evenly");
    const links = Array.from(host.querySelectorAll("a"));
    expect(links).toHaveLength(4);
    expect(links[0]?.getAttribute("href")).toBe("/home");
    expect(links[0]?.getAttribute("aria-label")).toBe("Home");
    expect(links[0]?.getAttribute("aria-current")).toBe("page");
    expect(links[0]?.className).toEqual(links[1]?.className);
    expect(links[0]?.className).not.toContain("text-accent");
    expect(links[1]?.getAttribute("href")).toBe("/upload");
    expect(links[1]?.getAttribute("aria-label")).toBe("Upload");
    expect(links[1]?.getAttribute("aria-current")).toBeNull();
    expect(links[2]?.getAttribute("href")).toBe("/budgets");
    expect(links[2]?.getAttribute("aria-label")).toBe("Budgets");
    expect(links[2]?.getAttribute("aria-current")).toBeNull();
    expect(links[3]?.getAttribute("href")).toBe("/account");
    expect(links[3]?.getAttribute("aria-label")).toBe("Account");
    expect(links.every((link) => link.querySelector("svg") !== null)).toBe(true);
  });

  it("PrimaryButton mounts and uses rounded-sm (not pill)", () => {
    act(() => {
      root.render(<PrimaryButton>Continue</PrimaryButton>);
    });
    const button = host.querySelector("button");
    expect(button?.textContent).toBe("Continue");
    expect(button?.className).toContain("rounded-sm");
    expect(button?.className).not.toContain("rounded-full");
  });

  it("SoftLedgerSelect opens a listbox and chooses an option", () => {
    const onChange = vi.fn();
    act(() => {
      root.render(
        <SoftLedgerSelect
          value="a"
          options={[
            { value: "a", label: "Alice" },
            { value: "b", label: "Bob" },
          ]}
          onChange={onChange}
          aria-label="Member"
        />,
      );
    });
    const trigger = host.querySelector("button[aria-haspopup='listbox']") as HTMLButtonElement;
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    act(() => {
      trigger.click();
    });
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(host.querySelector("[role='listbox']")).not.toBeNull();
    const alice = Array.from(host.querySelectorAll("[role='option']")).find(
      (el) => el.textContent === "Alice",
    ) as HTMLElement;
    const bob = Array.from(host.querySelectorAll("[role='option']")).find(
      (el) => el.textContent === "Bob",
    ) as HTMLElement;
    expect(alice.getAttribute("aria-selected")).toBe("true");
    expect(alice.className).toMatch(/itemSelected/);
    expect(alice.className).not.toContain("bg-accent");
    expect(bob.getAttribute("aria-selected")).toBe("false");
    expect(bob.className).not.toMatch(/itemSelected/);
    act(() => {
      bob.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    });
    expect(onChange).toHaveBeenCalledWith("b");
    expect(document.activeElement).not.toBe(trigger);
  });

  it("SoftLedgerSelect blurs the trigger after choosing, not after Escape", () => {
    const onChange = vi.fn();
    act(() => {
      root.render(
        <SoftLedgerSelect
          value="a"
          options={[
            { value: "a", label: "Alice" },
            { value: "b", label: "Bob" },
          ]}
          onChange={onChange}
          aria-label="Member"
        />,
      );
    });
    const trigger = host.querySelector("button[aria-haspopup='listbox']") as HTMLButtonElement;
    act(() => {
      trigger.focus();
      trigger.click();
    });
    const listbox = host.querySelector("[role='listbox']") as HTMLUListElement;
    expect(document.activeElement).toBe(listbox);
    act(() => {
      listbox.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).toBe(trigger);
    expect(onChange).not.toHaveBeenCalled();

    act(() => {
      trigger.click();
    });
    const bob = Array.from(host.querySelectorAll("[role='option']")).find(
      (el) => el.textContent === "Bob",
    ) as HTMLElement;
    act(() => {
      bob.dispatchEvent(new MouseEvent("mousedown", { bubbles: true }));
    });
    expect(onChange).toHaveBeenCalledWith("b");
    expect(document.activeElement).not.toBe(trigger);
  });

  it("SoftLedgerSelect blurs the trigger after Enter confirms the listbox value", () => {
    const onChange = vi.fn();
    act(() => {
      root.render(
        <SoftLedgerSelect
          value="a"
          options={[
            { value: "a", label: "Alice" },
            { value: "b", label: "Bob" },
          ]}
          onChange={onChange}
          aria-label="Member"
        />,
      );
    });
    const trigger = host.querySelector("button[aria-haspopup='listbox']") as HTMLButtonElement;
    act(() => {
      trigger.focus();
      trigger.click();
    });
    const listbox = host.querySelector("[role='listbox']") as HTMLUListElement;
    act(() => {
      listbox.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).not.toBe(trigger);
  });

  it("SoftLedgerSelect moves highlight with ArrowDown and confirms with Enter", () => {
    const onChange = vi.fn();
    act(() => {
      root.render(
        <SoftLedgerSelect
          value="a"
          options={[
            { value: "a", label: "Alice" },
            { value: "b", label: "Bob" },
          ]}
          onChange={onChange}
          aria-label="Member"
        />,
      );
    });
    const trigger = host.querySelector("button[aria-haspopup='listbox']") as HTMLButtonElement;
    act(() => {
      trigger.focus();
      trigger.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    const listbox = host.querySelector("[role='listbox']") as HTMLUListElement;
    expect(listbox).not.toBeNull();
    act(() => {
      listbox.focus();
      listbox.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
    });
    expect(onChange).toHaveBeenCalledWith("b");
    act(() => {
      listbox.dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
    });
    expect(trigger.getAttribute("aria-expanded")).toBe("false");
    expect(document.activeElement).not.toBe(trigger);
  });

  it("SoftLedgerSelect opens on ArrowUp from the trigger", () => {
    act(() => {
      root.render(
        <SoftLedgerSelect
          value="a"
          options={[
            { value: "a", label: "Alice" },
            { value: "b", label: "Bob" },
          ]}
          onChange={() => {}}
          aria-label="Member"
        />,
      );
    });
    const trigger = host.querySelector("button[aria-haspopup='listbox']") as HTMLButtonElement;
    act(() => {
      trigger.focus();
      trigger.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
    });
    expect(trigger.getAttribute("aria-expanded")).toBe("true");
    expect(host.querySelector("[role='listbox']")).not.toBeNull();
  });

  it("SoftLedgerRadio renders radio and checkbox with background outline fill", () => {
    const onChange = vi.fn();
    act(() => {
      root.render(
        <SoftLedgerRadio name="mode" checked={false} onChange={onChange}>
          Even
        </SoftLedgerRadio>,
      );
    });
    const input = host.querySelector('input[type="radio"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(host.textContent).toContain("Even");
    act(() => {
      input.click();
    });
    expect(onChange).toHaveBeenCalled();

    act(() => {
      root.render(
        <SoftLedgerRadio type="checkbox" checked onChange={() => { }}>
          Agree
        </SoftLedgerRadio>,
      );
    });
    expect(host.querySelector('input[type="checkbox"]')).not.toBeNull();

    const mark = host.querySelector("span[aria-hidden='true']");
    expect(mark?.className).toContain("border-accent");
    expect(mark?.className).toContain("peer-checked:bg-accent");
  });
});
