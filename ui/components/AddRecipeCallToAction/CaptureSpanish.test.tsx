/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearCapture, getCaptureState, openSheet } from "@/lib/capture/captureStore";

import { AddRecipeOptionsDialog } from "./AddRecipeOptionsDialog";
import { TextCaptureSheet } from "./TextCaptureSheet";

const prefs = vi.hoisted(() => ({ value: { locale: "es" } as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }));

const candidates = [
  { id: "nb-1", name: "Cuaderno de ana", kind: "personal" as const, kitchenId: null },
  { id: "nb-2", name: "Lista familiar", kind: "personal" as const, kitchenId: null },
];

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function setValue(element: HTMLTextAreaElement, value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value")!.set!;
  act(() => {
    setter.call(element, value);
    element.dispatchEvent(new Event("input", { bubbles: true }));
  });
}

describe("the add-recipe entry points in Spanish (spec 063)", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    clearCapture();
    prefs.value = { locale: "es" };
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(200, { max_text_chars: 5000 })));
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
  });

  it("the options dialog names its options in Spanish", () => {
    act(() => root.render(<AddRecipeOptionsDialog open onClose={() => {}} onChooseText={() => {}} />));
    const text = document.body.textContent ?? "";
    expect(text).toContain("Agregar una receta");
    expect(text).toContain("Texto");
    expect(text).toContain("Imagen");
    expect(text).toContain("Próximamente");
    expect(text).not.toContain("Add a recipe");
    expect(text).not.toContain("Coming soon");
  });

  it("the text sheet labels, counter and submit are Spanish", () => {
    openSheet({ id: "nb-1", kind: "personal", name: "Cuaderno de ana", kitchenId: null, returnPath: "/notebooks" });
    act(() => root.render(<TextCaptureSheet open candidates={candidates} onDraftReady={() => {}} />));
    setValue(document.querySelector("textarea")!, "2 cebollas");
    const text = document.body.textContent ?? "";
    expect(text).toContain("Texto de la receta");
    expect(text).toContain("Cuaderno");
    expect(text).toContain("Leer receta");
    expect(text).not.toContain("Read recipe");
  });

  it("an error from the assistant is Spanish and the text is kept", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(200, { max_text_chars: 5000 }))
        .mockResolvedValueOnce(json(422, { code: "not_a_recipe", detail: "not_food" })),
    );
    openSheet({ id: "nb-1", kind: "personal", name: "Cuaderno de ana", kitchenId: null, returnPath: "/notebooks" });
    act(() => root.render(<TextCaptureSheet open candidates={candidates} onDraftReady={() => {}} />));
    setValue(document.querySelector("textarea")!, "¿Qué tiempo hará mañana?");

    const submit = Array.from(document.querySelectorAll("button")).find(
      (b) => b.textContent === "Leer receta",
    ) as HTMLButtonElement;
    await act(async () => submit.click());

    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "Eso no parece una receta. No trata de comida. Pega la receta completa, con sus ingredientes y pasos.",
    );
    expect(document.querySelector("textarea")!.value).toBe("¿Qué tiempo hará mañana?");
    expect(getCaptureState().draft).toBeNull();
  });

  it("the length counter near the limit is Spanish", () => {
    openSheet({ id: "nb-1", kind: "personal", name: "Cuaderno de ana", kitchenId: null, returnPath: "/notebooks" });
    act(() => root.render(<TextCaptureSheet open candidates={candidates} onDraftReady={() => {}} />));
    setValue(document.querySelector("textarea")!, "x".repeat(4900));
    expect(document.body.textContent).toContain("4900 de 5000 caracteres");
  });

  it("the too-long message is Spanish", () => {
    openSheet({ id: "nb-1", kind: "personal", name: "Cuaderno de ana", kitchenId: null, returnPath: "/notebooks" });
    act(() => root.render(<TextCaptureSheet open candidates={candidates} onDraftReady={() => {}} />));
    setValue(document.querySelector("textarea")!, "x".repeat(5001));
    expect(document.querySelector("[role='alert']")?.textContent).toBe(
      "Ese texto es demasiado largo. Pega hasta 5000 caracteres.",
    );
  });
});
