/** @vitest-environment jsdom */

import { pickNotebook } from "@/components/NotebookPicker/testHelpers";
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { clearCapture, getCaptureState, openSheet } from "@/lib/capture/captureStore";

import { UrlCaptureSheet } from "./UrlCaptureSheet";

const prefs = vi.hoisted(() => ({ value: null as { locale: "en" | "es" } | null }));
vi.mock("@/components/PreferencesProvider", () => ({ useOptionalPreferences: () => prefs.value }));
const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));

const candidates = [
  { id: "nb-1", name: "ana's Notebook", kind: "personal" as const, kitchenId: null },
  { id: "nb-2", name: "Family list", kind: "personal" as const, kitchenId: null },
];
const LINK = "https://example.test/recipes/soup";

const okResponse = {
  outcome: "draft",
  notebook: { id: "nb-1", kind: "personal", name: "ana's Notebook", kitchen_id: null },
  language: "en",
  catalog: ["onion"],
  draft: {
    title: "Golden Lentil Soup",
    base_servings: 4,
    servings_estimated: false,
    changes: [],
    ingredient_lines: [
      {
        name: "onion",
        vague: false,
        quantity: 2,
        unit: "unit",
        size: "large",
        preparation: "chopped",
        note: null,
        text_name: "onions",
        match: { kind: "matched", entry: "onion" },
      },
    ],
    steps: ["Simmer."],
  },
  page: { source_url: LINK + "-final", preview_image: "data:image/jpeg;base64,AAAA", cut: true },
};

let container: HTMLDivElement;
let root: Root;

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function render() {
  act(() => {
    root.render(<UrlCaptureSheet open candidates={candidates} onDraftReady={() => push("/notebooks/draft")} />);
  });
}

function field(): HTMLInputElement {
  return document.querySelector("input[type='url']") as HTMLInputElement;
}

function type(value: string) {
  const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")!.set!;
  act(() => {
    setter.call(field(), value);
    field().dispatchEvent(new Event("input", { bubbles: true }));
  });
}

function submitButton(): HTMLButtonElement {
  return document.querySelector("button[type='submit']") as HTMLButtonElement;
}

function alertText(): string | null {
  return document.querySelector("[role='alert']")?.textContent ?? null;
}

beforeEach(() => {
  clearCapture();
  push.mockReset();
  prefs.value = null;
  openSheet({ id: "nb-1", kind: "personal", name: "ana's Notebook", kitchenId: null, returnPath: "/notebooks" }, "url");
  vi.stubGlobal("fetch", vi.fn());
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => root.unmount());
  container.remove();
  vi.unstubAllGlobals();
});

describe("UrlCaptureSheet", () => {
  it("shows one link field for URLs with its label", () => {
    render();

    expect(field().inputMode).toBe("url");
    expect(field().closest("label")?.textContent).toContain("Recipe link");
    expect(document.querySelector("textarea")).toBeNull();
  });

  it("keeps submit disabled while the field is empty, with no message", () => {
    render();

    expect(submitButton().disabled).toBe(true);
    type("   ");
    expect(submitButton().disabled).toBe(true);
    expect(alertText()).toBeNull();
  });

  it("shows the field message for something that is not a link", () => {
    render();

    type("example");

    expect(submitButton().disabled).toBe(true);
    expect(alertText()).toBe("Paste a link that starts with http:// or https://");
  });

  it("shows the field message for a link over 2,048 characters", () => {
    render();

    type("https://example.test/" + "a".repeat(2049));

    expect(submitButton().disabled).toBe(true);
    expect(alertText()).toBe("That link is too long.");
  });

  it("sends the link with https:// added, shows the loader, and opens the draft", async () => {
    let answer: (value: Response) => void = () => {};
    const fetchMock = vi.fn().mockReturnValue(new Promise<Response>((resolve) => (answer = resolve)));
    vi.stubGlobal("fetch", fetchMock);
    render();
    type("example.test/recipes/soup");

    await act(async () => submitButton().click());

    // The loader is on the button, not a separate one in the sheet.
    expect(submitButton().getAttribute("aria-busy")).toBe("true");
    expect(submitButton().querySelector("svg")).not.toBeNull();
    expect(document.querySelector("[role='status']")).toBeNull();
    expect(submitButton().disabled).toBe(true);
    // A second press while waiting sends nothing (FR-004).
    await act(async () => submitButton().click());
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/notebooks/nb-1/captures/url");
    expect(JSON.parse(init.body)).toEqual({ url: LINK });

    await act(async () => answer(json(200, okResponse)));

    expect(push).toHaveBeenCalledWith("/notebooks/draft");
    const draft = getCaptureState().draft;
    expect(draft?.title).toBe("Golden Lentil Soup");
    expect(draft?.sourceUrl).toBe(LINK + "-final");
    expect(draft?.previewImage).toBe("data:image/jpeg;base64,AAAA");
    expect(draft?.pageCut).toBe(true);
  });

  it("sends to the notebook chosen in the picker", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json(422, { code: "page_no_recipe", detail: "" }));
    vi.stubGlobal("fetch", fetchMock);
    render();
    pickNotebook("Family list");
    type(LINK);

    await act(async () => submitButton().click());

    expect(fetchMock.mock.calls[0][0]).toBe("/api/notebooks/nb-2/captures/url");
    expect(field().value).toBe(LINK);
  });

  // T055: every refusal shows its message and keeps the link (FR-023, FR-025, SC-004).
  it.each<[string, Record<string, unknown>, number, string]>([
    ["page_fetch_failed", {}, 422, "We couldn't open that page. Paste the recipe text instead."],
    ["site_requires_license", {}, 422, "This website requires a license, it's not supported yet."],
    ["page_no_recipe", {}, 422, "We couldn't find a recipe on that page. Paste the recipe text instead."],
    ["link_invalid", {}, 422, "Paste a link that starts with http:// or https://"],
    ["link_empty", {}, 422, "Paste a link that starts with http:// or https://"],
    ["link_too_long", { max: 2048 }, 422, "That link is too long."],
    ["one_recipe_at_a_time", {}, 422, "Only one recipe can be added at a time. Paste them one by one."],
    ["ai_unavailable", {}, 503, "The assistant isn't responding. Your link is kept — try again."],
    ["ai_misconfigured", {}, 503, "Assistant misconfigured. Your link is kept"],
    ["ai_limit_reached", {}, 429, "We've hit the assistant's limit. Try again in a minute."],
    [
      "ai_invalid_output",
      {},
      422,
      "The app could not build a recipe from this text. Try again, or shorten the text to one recipe.",
    ],
    ["draft_incomplete", { missing: ["steps"], line_problems: [] }, 422, "Add the steps of the recipe."],
    ["kitchen_archived", {}, 409, "This kitchen is archived, so recipes can't be added."],
  ])("%s shows its message and keeps the link", async (code, extra, status, expected) => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(status, { code, detail: "", ...extra })));
    render();
    type(LINK);

    await act(async () => submitButton().click());

    expect(alertText()).toBe(expected);
    expect(field().value).toBe(LINK);
    expect(submitButton().disabled).toBe(false);
  });

  it("a network failure keeps the link and says so", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    render();
    type(LINK);

    await act(async () => submitButton().click());

    expect(alertText()).toBe("The assistant isn't responding. Your link is kept — try again.");
    expect(field().value).toBe(LINK);
  });

  it("editing the link clears the last message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(422, { code: "page_fetch_failed", detail: "" })));
    render();
    type(LINK);
    await act(async () => submitButton().click());

    type(LINK + "/other");

    expect(alertText()).toBeNull();
  });
});

describe("UrlCaptureSheet in Spanish (spec 063)", () => {
  beforeEach(() => {
    prefs.value = { locale: "es" };
  });

  it("labels the field and shows each refusal in Spanish, keeping the link", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(json(422, { code: "page_fetch_failed", detail: "" }))
        .mockResolvedValueOnce(json(422, { code: "page_no_recipe", detail: "" }))
        .mockResolvedValueOnce(json(422, { code: "site_requires_license", detail: "" }))
        .mockResolvedValueOnce(json(503, { code: "ai_misconfigured", detail: "" })),
    );
    render();
    expect(field().closest("label")?.textContent).toContain("Enlace de la receta");
    type(LINK);

    await act(async () => submitButton().click());
    expect(alertText()).toBe("No pudimos abrir esa página. Pega el texto de la receta.");

    await act(async () => submitButton().click());
    expect(alertText()).toBe("No encontramos una receta en esa página. Pega el texto de la receta.");

    await act(async () => submitButton().click());
    expect(alertText()).toBe("Este sitio web requiere una licencia, aún no es compatible.");

    await act(async () => submitButton().click());
    expect(alertText()).toBe("El asistente está mal configurado. Tu enlace se conserva.");
    expect(field().value).toBe(LINK);
  });

  it("shows the field messages in Spanish", () => {
    render();

    type("example");
    expect(alertText()).toBe("Pega un enlace que empiece por http:// o https://");

    type("https://example.test/" + "a".repeat(2049));
    expect(alertText()).toBe("Ese enlace es demasiado largo.");
  });
});
