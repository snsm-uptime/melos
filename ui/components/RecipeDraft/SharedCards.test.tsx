/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { LineView } from "@/lib/capture/captureStore";

import { IngredientLineRow } from "./IngredientLineRow";
import { NameChangeNotice } from "./NameChangeNotice";
import { RowControls } from "./RowControls";
import { StepCard } from "./StepCard";

const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));

const line: LineView = {
  key: "l1",
  name: "cebolla",
  vague: false,
  quantity: 2,
  unit: "unit",
  size: "large",
  preparation: "picada",
  note: null,
  textName: "cebollas",
  match: { kind: "matched", entry: "cebolla" },
};

describe("shared draft cards follow the interface language (spec 063 FR-007)", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    prefs.value = null;
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
  });

  const render = (node: React.ReactNode) => act(() => root.render(node));
  const labels = () =>
    Array.from(container.querySelectorAll("[aria-label], [placeholder], label, h3, button")).flatMap(
      (el) => [el.getAttribute("aria-label"), el.getAttribute("placeholder"), el.textContent],
    );

  const editable = (locale?: "en" | "es") => (
    <ul>
      <IngredientLineRow
        line={line}
        index={0}
        count={2}
        errors={["amountAndUnit"]}
        units={["g", "unit"]}
        sizes={["small", "large"]}
        catalog={["cebolla"]}
        change={{ line: 0, from: "cebollas", to: "cebolla" }}
        onUndoChange={() => {}}
        onChange={() => {}}
        onRemove={() => {}}
        onMove={() => {}}
        locale={locale}
      />
    </ul>
  );

  it("the editable row, its controls, its notice and its errors are Spanish by locale prop", () => {
    render(editable("es"));
    const text = labels().join("|");
    for (const expected of ["Nombre", "Cantidad", "Unidad", "Tamaño", "Cantidad imprecisa", "Preparación", "Nota", "Quitar", "Subir", "Bajar", "Deshacer", "Coincidencia del catálogo"]) {
      expect(text, expected).toContain(expected);
    }
    expect(container.textContent).toContain("cebollas → cebolla");
    expect(container.textContent).toContain("Agrega una cantidad y una unidad, o márcala como imprecisa.");
    expect(text).not.toMatch(/\b(Quantity|Unit|Remove|Move up|Undo|Preparation)\b/);
  });

  it("takes the language from the provider when no locale is given", () => {
    prefs.value = { locale: "es" };
    render(editable());
    expect(labels().join("|")).toContain("Quitar");
    expect(container.textContent).toContain("ingrediente nuevo");
  });

  it("stays English for English", () => {
    render(editable("en"));
    expect(labels().join("|")).toContain("Remove");
    expect(container.textContent).toContain("new ingredient");
  });

  it("the read-only row labels are Spanish and show stored text as stored", () => {
    render(
      <ul>
        <IngredientLineRow line={{ ...line, note: "to taste" }} readOnly locale="es" />
      </ul>,
    );
    expect(container.textContent).toContain("Preparación:");
    expect(container.textContent).toContain("Nota:");
    expect(container.textContent).toContain("picada");
    expect(container.textContent).toContain("to taste");
    expect(container.textContent).toContain("cebolla");
  });

  it("the step card is Spanish editable and read-only", () => {
    render(
      <ol>
        <StepCard index={0} count={2} text="Hervir" onChange={() => {}} onRemove={() => {}} onMove={() => {}} locale="es" />
      </ol>,
    );
    expect(container.querySelector("textarea")?.getAttribute("aria-label")).toBe("Paso 1");
    expect(container.querySelector("[aria-label=Quitar]")).not.toBeNull();
    act(() => root.unmount());
    root = createRoot(container);
    render(
      <ol>
        <StepCard index={1} text="Hervir" readOnly locale="es" />
      </ol>,
    );
    expect(container.textContent).toContain("Hervir");
    expect(container.querySelector("textarea, button")).toBeNull();
  });

  it("the row controls and the notice are Spanish on their own", () => {
    render(
      <div>
        <RowControls index={0} count={2} onRemove={() => {}} onMove={() => {}} locale="es" />
        <NameChangeNotice change={{ line: 0, from: "a", to: "b" }} onUndo={() => {}} locale="es" />
      </div>,
    );
    expect(container.querySelector("[aria-label=Quitar]")).not.toBeNull();
    expect(container.querySelector("[aria-label=Bajar]")).not.toBeNull();
    expect(container.textContent).toContain("Deshacer");
  });
});
