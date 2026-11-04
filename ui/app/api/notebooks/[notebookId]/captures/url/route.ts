import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

type RouteContext = {
  params: Promise<{ notebookId: string }>;
};

/** Seconds the api may spend fetching the page (spec 026, PRD §1.7). */
const PAGE_FETCH_S = 10;

/**
 * The page fetch, then the assistant's own timeout (the batches run at the same time), plus a
 * margin, so a stalled api still gets an answer (spec 026 research R11).
 */
function deadlineMs(): number {
  const seconds = Number(process.env.GEMINI_TEXT_TIMEOUT_S) || 10;
  return (PAGE_FETCH_S + seconds + 2) * 1000;
}

/**
 * Same-origin BFF: POST /api/notebooks/{id}/captures/url → api. Status, body and Retry-After
 * pass through unchanged. A timeout or a network failure is answered here as ai_unavailable.
 * The browser never contacts the recipe site: the api fetches the page and its photo.
 */
export async function POST(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;

  let body: string;
  try {
    body = JSON.stringify(await request.json());
  } catch {
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
      `${getApiInternalUrl()}/notebooks/${encodeURIComponent(notebookId)}/captures/url`,
      { method: "POST", headers, body, cache: "no-store", signal: controller.signal },
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
