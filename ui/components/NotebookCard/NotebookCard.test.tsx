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

  it("links to the recipe list when given an href", () => {
    render({ recipeCount: 0, name: "Family", ownerAlias: "ben", locale: "en", href: "/notebooks/nb-1" });

    const link = container.querySelector("a");
    expect(link?.getAttribute("href")).toBe("/notebooks/nb-1");
    expect(link?.textContent).toContain("Family");
  });

  it("renders no link and no button without an href", () => {
    render({ recipeCount: 0, name: "ana's Notebook", ownerAlias: "ana", locale: "en", isDefault: true, access: "owner" });

    expect(container.querySelector("a")).toBeNull();
    expect(container.querySelector("button")).toBeNull();
  });

  it("shows the bookmark only when isDefault is true", () => {
    render({ recipeCount: 0, name: "ana's Notebook", ownerAlias: "ana", locale: "en", isDefault: true });
    expect(container.querySelector('[role="img"]')?.getAttribute("aria-label")).toBe("Default");
    expect(container.textContent).not.toContain("Default");

    render({ recipeCount: 0, name: "ana's (Home) Notebook", ownerAlias: "ana", locale: "en" });
    expect(container.querySelector('[role="img"]')).toBeNull();
  });

  it("shows how many recipes it has", () => {
    render({ recipeCount: 1, name: "Family", ownerAlias: "ben", locale: "en" });
    expect(container.textContent).toContain("1 recipe");

    render({ recipeCount: 12, name: "Family", ownerAlias: "ben", locale: "es" });
    expect(container.textContent).toContain("12 recetas");
  });

  it("does not cut the name short", () => {
    render({ recipeCount: 0, name: "Family", ownerAlias: "ben", locale: "en" });
    expect(container.querySelector("h3")?.className).not.toContain("truncate");
  });

  it("shows the owner in an accent chip and other access in a muted one", () => {
    render({ recipeCount: 0, name: "Family", ownerAlias: "ben", locale: "en", access: "member" });

    const owner = [...container.querySelectorAll("span")].find((el) =>
      el.textContent?.endsWith("ben"),
    );
    expect(owner?.className).toContain("text-accent");
    const member = [...container.querySelectorAll("span")].find((el) => el.textContent === "Member");
    expect(member?.className).toContain("text-muted");
  });

  it("shows the viewer's own notebook with an accent Owner chip", () => {
    render({ recipeCount: 0, name: "ana's Notebook", ownerAlias: "ana", viewerAlias: "ana", locale: "en", access: "owner" });

    const owner = [...container.querySelectorAll("span")].find((el) => el.textContent === "Owner");
    expect(owner?.className).toContain("text-accent");
  });

  it("shows unknown when the owner alias is null", () => {
    render({ recipeCount: 0, name: "Shared", ownerAlias: null, locale: "en" });
    expect(container.textContent).toContain("unknown");
  });

  it("shows access only when it is passed", () => {
    render({ recipeCount: 0, name: "Shared", ownerAlias: "ana", locale: "en" });
    expect(container.textContent).not.toContain("Owner");
    expect(container.textContent).not.toContain("Member");

    render({ recipeCount: 0, name: "Shared", ownerAlias: "ana", locale: "en", access: "kitchen_member" });
    expect(container.textContent).toContain("Kitchen member");
  });

  it("hides the owner line when the owner is the viewer", () => {
    render({ recipeCount: 0, name: "ana's Notebook", ownerAlias: "ana", locale: "en", viewerAlias: "ana" });
    expect(container.textContent).not.toContain("Owned by");

    render({ recipeCount: 0, name: "Family", ownerAlias: "ben", locale: "en", viewerAlias: "ana" });
    expect(container.textContent).toContain("Owned by ben");
  });

  it("still shows unknown for a null owner, even when the viewer has no alias", () => {
    render({ recipeCount: 0, name: "Shared", ownerAlias: null, locale: "en", viewerAlias: null });
    expect(container.textContent).toContain("Owned by unknown");
  });

  it("switches labels with the locale and keeps the name as stored", () => {
    render({ recipeCount: 0, name: "ana's Notebook", ownerAlias: "ana", locale: "es", isDefault: true, access: "owner" });

    expect(container.querySelector('[role="img"]')?.getAttribute("aria-label")).toBe("Predeterminado");
    expect(container.textContent).toContain("Propiedad de ana");
    expect(container.textContent).toContain("ana's Notebook");
  });
});
