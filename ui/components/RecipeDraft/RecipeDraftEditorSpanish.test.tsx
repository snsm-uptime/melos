/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  clearCapture,
  editDraft,
  failSave,
  getCaptureState,
  openSheet,
  setText,
  showDraft,
  type DraftView,
} from "@/lib/capture/captureStore";

import { LeaveDraftGuard } from "./LeaveDraftGuard";
import { RecipeDraftEditor } from "./RecipeDraftEditor";

const prefs = vi.hoisted(() => ({ value: { locale: "es" } as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

const draft: DraftView = {
  title: "Sopa de cebolla",
  baseServings: 4,
  servingsEstimated: true,
  lines: [
    {
      key: "l1",
      name: "cebollas",
      vague: false,
      quantity: 2,
      unit: "unit",
      size: "large",
      preparation: "picada",
      note: null,
      textName: "cebollas",
      match: { kind: "new", entry: null },
    },
  ],
  steps: [{ key: "s1", text: "Hervir." }],
  catalog: ["cebolla"],
};

describe("the draft editor in Spanish (spec 063)", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    clearCapture();
    prefs.value = { locale: "es" };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    openSheet({ id: "nb-1", kind: "personal", name: "Cuaderno de ana", kitchenId: null, returnPath: "/notebooks" });
    setText("2 cebollas grandes, picadas.");
    showDraft(draft, "es");
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  it("every label, button and card is Spanish and the recipe text is as stored", async () => {
    await act(async () => root.render(<RecipeDraftEditor />));
    const text = container.textContent ?? "";
    for (const expected of ["Ingredientes", "Pasos", "Porciones base", "Agregar ingrediente", "Agregar paso", "Descartar", "Guardar receta", "ingrediente nuevo"]) {
      expect(text, expected).toContain(expected);
    }
    expect((container.querySelector("h1 textarea") as HTMLTextAreaElement).value).toBe("Sopa de cebolla");
    expect(container.querySelector("[aria-label='Título']")).not.toBeNull();
    expect(container.querySelector("[aria-label='Paso 1']")).not.toBeNull();
    expect(text).not.toMatch(/\b(Ingredients|Steps|Discard|Save recipe|Add ingredient)\b/);
  });

  it("the field errors are Spanish", async () => {
    await act(async () => root.render(<RecipeDraftEditor />));
    act(() => editDraft({ ...getCaptureState().draft!, title: "", steps: [] }));
    expect(container.textContent).toContain("Agrega un título.");
    expect(container.textContent).toContain("Agrega al menos un paso.");
  });

  it("a save error is Spanish and the draft stays", async () => {
    await act(async () => root.render(<RecipeDraftEditor />));
    act(() => failSave({ code: "save_unavailable" }));
    expect(container.querySelector("[role=alert]")?.textContent).toBe(
      "No pudimos guardar la receta. Tus cambios se conservan. Inténtalo de nuevo.",
    );
  });

  it("the leave dialog is Spanish", async () => {
    await act(async () => root.render(<><RecipeDraftEditor /><LeaveDraftGuard /><a href="/home">home</a></>));
    act(() => editDraft({ ...getCaptureState().draft!, title: "Otro título" }));
    const link = container.querySelector("a[href='/home']") as HTMLAnchorElement;
    act(() => {
      link.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
    });
    const text = document.body.textContent ?? "";
    expect(text).toContain("¿Salir sin guardar?");
    expect(text).toContain("Perderás los cambios de este borrador.");
    expect(text).toContain("Quedarme");
  });
});
