import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

/** How long Save may take before the member is told it did not finish (spec 020). */
const DEADLINE_MS = 15_000;

/**
 * Same-origin BFF: POST /api/recipes → api. Status and body pass through unchanged. A timeout
 * or a network failure is answered here as save_unavailable (spec 020 contracts/save-ui.md).
 */
export async function POST(request: NextRequest) {
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

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), DEADLINE_MS);
  let upstream: Response;
  try {
    upstream = await fetch(`${getApiInternalUrl()}/recipes`, {
      method: "POST",
      headers,
      body,
      cache: "no-store",
      signal: controller.signal,
    });
  } catch {
    return NextResponse.json(
      { detail: "The recipe could not be saved.", code: "save_unavailable" },
      { status: 503 },
    );
  } finally {
    clearTimeout(timer);
  }

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") || "application/json" },
  });
}
