import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "./route";

const context = { params: Promise.resolve({ notebookId: "nb-1" }) };

function request(body: string) {
  return new NextRequest("http://localhost/api/notebooks/nb-1/captures/picture", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Cookie: "melos_session=abc",
      "Accept-Language": "es",
    },
    body,
  });
}

beforeEach(() => {
  vi.stubEnv("GEMINI_IMAGE_TIMEOUT_S", "30");
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("POST /api/notebooks/[notebookId]/captures/picture", () => {
  it("passes a draft through and forwards the cookie and the language", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ outcome: "draft" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const response = await POST(
      request(JSON.stringify({ image_base64: "AAAA", handwritten: true })),
      context,
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ outcome: "draft" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/notebooks\/nb-1\/captures\/picture$/);
    expect(JSON.parse(init.body)).toEqual({ image_base64: "AAAA", handwritten: true });
    expect(init.headers.get("Cookie")).toBe("melos_session=abc");
    expect(init.headers.get("Accept-Language")).toBe("es");
  });

  it("passes the status, body and Retry-After through unchanged", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ code: "ai_limit_reached" }), {
          status: 429,
          headers: { "Content-Type": "application/json", "Retry-After": "12" },
        }),
      ),
    );

    const response = await POST(request(JSON.stringify({ image_base64: "AAAA" })), context);

    expect(response.status).toBe(429);
    expect(response.headers.get("Retry-After")).toBe("12");
    expect(await response.json()).toEqual({ code: "ai_limit_reached" });
  });

  it("answers ai_unavailable when the network fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network")));

    const response = await POST(request(JSON.stringify({ image_base64: "AAAA" })), context);

    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ code: "ai_unavailable" });
  });

  it("answers ai_unavailable when the api is too slow", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init: { signal: AbortSignal }) =>
          new Promise((_resolve, reject) => {
            init.signal.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
          }),
      ),
    );

    const pending = POST(request(JSON.stringify({ image_base64: "AAAA" })), context);
    await vi.advanceTimersByTimeAsync(32_000);
    const response = await pending;

    expect(response.status).toBe(503);
    expect(await response.json()).toMatchObject({ code: "ai_unavailable" });
  });

  it("answers picture_too_large for a body that is not valid JSON", async () => {
    const response = await POST(request('{"image_base64": "AAAA'), context);
    expect(response.status).toBe(422);
    expect(await response.json()).toMatchObject({ code: "picture_too_large" });
  });

  it("answers invalid_body for a valid JSON body of the wrong shape", async () => {
    const response = await POST(request(JSON.stringify({ image_base64: 42 })), context);
    expect(response.status).toBe(400);
    expect(await response.json()).toMatchObject({ code: "invalid_body" });
  });

  it("forwards handwritten unchanged when it is false", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    await POST(request(JSON.stringify({ image_base64: "AAAA", handwritten: false })), context);
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      image_base64: "AAAA",
      handwritten: false,
    });
  });
});
