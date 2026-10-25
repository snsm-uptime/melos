/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";

import { NotebookCard } from "./NotebookCard";

describe("NotebookCard", () => {
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

  function render(props: Parameters<typeof NotebookCard>[0]) {
    act(() => {
      root.render(<NotebookCard {...props} />);
    });
  }

  it("renders no link and no button", () => {
    render({ name: "ana's Notebook", ownerAlias: "ana", locale: "en", isDefault: true, access: "owner" });

    expect(container.querySelector("a")).toBeNull();
    expect(container.querySelector("button")).toBeNull();
  });

  it("shows Default only when isDefault is true", () => {
    render({ name: "ana's Notebook", ownerAlias: "ana", locale: "en", isDefault: true });
    expect(container.textContent).toContain("Default");

    render({ name: "ana's (Home) Notebook", ownerAlias: "ana", locale: "en" });
    expect(container.textContent).not.toContain("Default");
  });

  it("shows unknown when the owner alias is null", () => {
    render({ name: "Shared", ownerAlias: null, locale: "en" });
    expect(container.textContent).toContain("unknown");
  });

  it("shows access only when it is passed", () => {
    render({ name: "Shared", ownerAlias: "ana", locale: "en" });
    expect(container.textContent).not.toContain("Owner");
    expect(container.textContent).not.toContain("Member");

    render({ name: "Shared", ownerAlias: "ana", locale: "en", access: "kitchen_member" });
    expect(container.textContent).toContain("Kitchen member");
  });

  it("hides the owner line when the owner is the viewer", () => {
    render({ name: "ana's Notebook", ownerAlias: "ana", locale: "en", viewerAlias: "ana" });
    expect(container.textContent).not.toContain("Owned by");

    render({ name: "Family", ownerAlias: "ben", locale: "en", viewerAlias: "ana" });
    expect(container.textContent).toContain("Owned by ben");
  });

  it("still shows unknown for a null owner, even when the viewer has no alias", () => {
    render({ name: "Shared", ownerAlias: null, locale: "en", viewerAlias: null });
    expect(container.textContent).toContain("Owned by unknown");
  });

  it("switches labels with the locale and keeps the name as stored", () => {
    render({ name: "ana's Notebook", ownerAlias: "ana", locale: "es", isDefault: true, access: "owner" });

    expect(container.textContent).toContain("Predeterminado");
    expect(container.textContent).toContain("Propiedad de ana");
    expect(container.textContent).toContain("ana's Notebook");
  });
});
