import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

type RouteContext = {
  params: Promise<{ notebookId: string }>;
};

/**
 * The api waits for the assistant (GEMINI_IMAGE_TIMEOUT_S, 30 s by default) and then answers.
 * The margin lets a stalled api still get an answer (spec 041 research R11).
 */
function deadlineMs(): number {
  const seconds = Number(process.env.GEMINI_IMAGE_TIMEOUT_S) || 30;
  return (seconds + 2) * 1000;
}

/** The body is JSON with a string `image_base64` and an optional boolean `handwritten`. */
function isPictureBody(value: unknown): value is { image_base64: string; handwritten?: boolean } {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const row = value as { image_base64?: unknown; handwritten?: unknown };
  if (typeof row.image_base64 !== "string") return false;
  return row.handwritten === undefined || typeof row.handwritten === "boolean";
}

/**
 * Same-origin BFF: POST /api/notebooks/{id}/captures/picture → api (spec 041). Status, body and
 * Retry-After pass through unchanged. A timeout or a network failure is answered here as
 * ai_unavailable. A body that is not JSON (a truncated upload) is answered as picture_too_large,
 * because that is the only way a picture body arrives broken.
 */
export async function POST(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;

  let parsed: unknown;
  try {
    parsed = await request.json();
  } catch {
    return NextResponse.json(
      { detail: "", code: "picture_too_large" },
      { status: 422 },
    );
  }
  if (!isPictureBody(parsed)) {
    return NextResponse.json({ detail: "Invalid request body.", code: "invalid_body" }, { status: 400 });
  }

  const headers = new Headers({
    Accept: "application/json",
    "Content-Type": "application/json",
  });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);
  const forwarded = request.headers.get("accept-language");
  if (forwarded) headers.set("Accept-Language", forwarded);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), deadlineMs());
  let upstream: Response;
  try {
    upstream = await fetch(
      `${getApiInternalUrl()}/notebooks/${encodeURIComponent(notebookId)}/captures/picture`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(parsed),
        cache: "no-store",
        signal: controller.signal,
      },
    );
  } catch {
    return NextResponse.json(
      { detail: "The assistant did not answer in time.", code: "ai_unavailable" },
      { status: 503 },
    );
  } finally {
    clearTimeout(timer);
  }

  const text = await upstream.text();
  const responseHeaders = new Headers({
    "Content-Type": upstream.headers.get("Content-Type") || "application/json",
  });
  const retryAfter = upstream.headers.get("Retry-After");
  if (retryAfter) responseHeaders.set("Retry-After", retryAfter);
  return new NextResponse(text, { status: upstream.status, headers: responseHeaders });
}
