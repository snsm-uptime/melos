import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

const context = { params: Promise.resolve({ notebookId: "nb-1" }) };

function request(body: string) {
  return new NextRequest("http://localhost/api/notebooks/nb-1/captures/url", {
    method: "POST",
    headers: { "Content-Type": "application/json", Cookie: "melos_session=abc", "Accept-Language": "es" },
    body,
  });
}

beforeEach(() => {
  vi.stubEnv("GEMINI_TEXT_TIMEOUT_S", "10");
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("POST /api/notebooks/[notebookId]/captures/url", () => {
  it("forwards the link, the cookie and the language, and passes the answer through", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "page_fetch_failed", detail: "" }), {
        status: 422,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(request(JSON.stringify({ url: "https://example.test/soup" })), context);

    expect(response.status).toBe(422);
    expect(await response.json()).toEqual({ code: "page_fetch_failed", detail: "" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/notebooks\/nb-1\/captures\/url$/);
    expect(JSON.parse(init.body)).toEqual({ url: "https://example.test/soup" });
    expect(init.headers.get("Cookie")).toBe("melos_session=abc");
    expect(init.headers.get("Accept-Language")).toBe("es");
  });

  it("passes Retry-After through", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ code: "ai_limit_reached" }), {
          status: 429,
          headers: { "Content-Type": "application/json", "Retry-After": "12" },
        }),
      ),
    );

    const response = await POST(request(JSON.stringify({ url: "https://example.test/" })), context);

    expect(response.status).toBe(429);
    expect(response.headers.get("Retry-After")).toBe("12");
  });

  it("answers 400 invalid_body without calling the api when the body is not JSON", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(request("not json"), context);

    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("answers 503 ai_unavailable when the api cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("down")));

    const response = await POST(request(JSON.stringify({ url: "https://example.test/" })), context);

    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ code: "ai_unavailable" });
  });

  it("waits for the page fetch plus the assistant timeout plus two seconds", async () => {
    vi.stubEnv("GEMINI_TEXT_TIMEOUT_S", "1");
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise((_resolve, reject) => {
            init.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
          }),
      ),
    );

    const pending = POST(request(JSON.stringify({ url: "https://example.test/" })), context);
    await vi.advanceTimersByTimeAsync(12_999);
    expect(
      await Promise.race([pending.then(() => "answered"), Promise.resolve("waiting")]),
    ).toBe("waiting");
    await vi.advanceTimersByTimeAsync(1);

    const response = await pending;
    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ code: "ai_unavailable" });
  });
});
