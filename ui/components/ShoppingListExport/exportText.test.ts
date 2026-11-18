import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchExportPdf, fetchExportText, hasItems } from "./exportText";

describe("export client", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the Markdown text on success", async () => {
    fetchMock.mockResolvedValue(
      new Response("- rice — 2 cup\n", { status: 200 }),
    );
    const result = await fetchExportText("k1", "l1");
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/kitchens/k1/shopping-lists/l1/export?format=markdown",
    );
    expect(result).toEqual({ ok: true, value: "- rice — 2 cup\n" });
  });

  it("returns the status on a 404 without a body code", async () => {
    fetchMock.mockResolvedValue(
      new Response('{"detail":"Not found"}', { status: 404 }),
    );
    expect(await fetchExportText("k1", "l1")).toEqual({
      ok: false,
      status: 404,
      code: null,
    });
  });

  it("returns status 0 when the network fails", async () => {
    fetchMock.mockRejectedValue(new TypeError("offline"));
    expect(await fetchExportText("k1", "l1")).toEqual({
      ok: false,
      status: 0,
      code: null,
    });
  });

  it("returns the PDF bytes with the file name the api sent", async () => {
    fetchMock.mockResolvedValue(
      new Response(new Blob(["%PDF-1.4"]), {
        status: 200,
        headers: {
          "Content-Type": "application/pdf",
          "Content-Disposition":
            'attachment; filename="shopping-list-2026-11-17.pdf"',
        },
      }),
    );
    const result = await fetchExportPdf("k1", "l1");
    expect(fetchMock.mock.calls[0][0]).toBe(
      "/api/kitchens/k1/shopping-lists/l1/export?format=pdf",
    );
    expect(result.ok).toBe(true);
    if (!result.ok) return;
    expect(result.value.fileName).toBe("shopping-list-2026-11-17.pdf");
    expect(result.value.blob.size).toBe(8);
  });

  it("reports a failed PDF as not ok", async () => {
    fetchMock.mockResolvedValue(
      new Response('{"detail":"PDF could not be created"}', { status: 500 }),
    );
    expect(await fetchExportPdf("k1", "l1")).toEqual({
      ok: false,
      status: 500,
      code: null,
    });
  });
});

describe("hasItems", () => {
  it("is true when the Markdown has an item line", () => {
    expect(hasItems("## Shopping list\n\n- rice — 2 cup\n")).toBe(true);
  });

  it("is false for the empty list text", () => {
    expect(hasItems("## Shopping list (2026-11-17)\n\nNo items\n")).toBe(false);
  });
});
