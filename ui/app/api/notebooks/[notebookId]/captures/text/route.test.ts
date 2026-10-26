import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

const context = { params: Promise.resolve({ notebookId: "nb-1" }) };

function request(body: string, contentType = "application/json") {
  return new NextRequest("http://localhost/api/notebooks/nb-1/captures/text", {
    method: "POST",
    headers: { "Content-Type": contentType, Cookie: "melos_session=abc" },
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

describe("POST /api/notebooks/[notebookId]/captures/text", () => {
  it("passes status, body and Retry-After through unchanged, and forwards the cookie", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ code: "ai_limit_reached" }), {
        status: 429,
        headers: { "Content-Type": "application/json", "Retry-After": "30" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(request(JSON.stringify({ text: "2 onions" })), context);

    expect(response.status).toBe(429);
    expect(response.headers.get("Retry-After")).toBe("30");
    expect(await response.json()).toEqual({ code: "ai_limit_reached" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/notebooks\/nb-1\/captures\/text$/);
    expect(init.headers.get("Cookie")).toBe("melos_session=abc");
  });

  it("answers 400 invalid_body without calling the api when the body is not JSON", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(request("not json"), context);

    expect(response.status).toBe(400);
    expect(await response.json()).toMatchObject({ code: "invalid_body" });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("answers 503 ai_unavailable when the api cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("down")));

    const response = await POST(request(JSON.stringify({ text: "x" })), context);

    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ code: "ai_unavailable" });
  });

  it("aborts after the assistant timeout plus two seconds and answers 503 ai_unavailable", async () => {
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

    const pending = POST(request(JSON.stringify({ text: "x" })), context);
    await vi.advanceTimersByTimeAsync(2999);
    expect(
      await Promise.race([pending.then(() => "answered"), Promise.resolve("waiting")]),
    ).toBe("waiting");
    await vi.advanceTimersByTimeAsync(1);

    const response = await pending;
    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ code: "ai_unavailable" });
  });
});
