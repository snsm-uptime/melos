import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

/** How long Save may take before the member is told it did not finish (spec 020, 027). */
export const RECIPE_WRITE_DEADLINE_MS = 15_000;

type ForwardOptions = {
  method: "GET" | "POST" | "PUT" | "DELETE";
  path: string;
  /** Read the JSON body of the incoming request and send it on. */
  withBody?: boolean;
  /** A timeout or network failure is answered here, as save_unavailable (contracts/recipe-ui.md). */
  deadlineMs?: number;
};

/**
 * Same-origin BFF for the recipe routes of spec 027: the session cookie goes on, the status and
 * body come back unchanged. A 204 stays empty. The api is the only cookie issuer.
 */
export async function forwardRecipeRequest(
  request: NextRequest,
  { method, path, withBody = false, deadlineMs }: ForwardOptions,
): Promise<NextResponse> {
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let body: string | undefined;
  if (withBody) {
    try {
      body = JSON.stringify(await request.json());
    } catch {
      return NextResponse.json(
        { detail: "Invalid request body.", code: "invalid_body" },
        { status: 400 },
      );
    }
    headers.set("Content-Type", "application/json");
  }

  const controller = new AbortController();
  const timer = deadlineMs ? setTimeout(() => controller.abort(), deadlineMs) : null;
  let upstream: Response;
  try {
    upstream = await fetch(`${getApiInternalUrl()}${path}`, {
      method,
      headers,
      body,
      cache: "no-store",
      signal: controller.signal,
    });
  } catch {
    return deadlineMs
      ? NextResponse.json(
          { detail: "The recipe could not be saved.", code: "save_unavailable" },
          { status: 503 },
        )
      : NextResponse.json({ detail: "Upstream unavailable.", code: "bad_gateway" }, { status: 502 });
  } finally {
    if (timer) clearTimeout(timer);
  }

  if (upstream.status === 204) return new NextResponse(null, { status: 204 });
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": upstream.headers.get("Content-Type") || "application/json" },
  });
}
