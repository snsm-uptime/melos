import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";
import { forwardRecipeRequest } from "@/lib/recipeBff";

/**
 * Same-origin BFF: /api/notebooks → api /notebooks (the caller's personal notebooks).
 */
export async function GET(request: NextRequest) {
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let upstream: Response;
  try {
    upstream = await fetch(`${getApiInternalUrl()}/notebooks`, {
      method: "GET",
      headers,
      cache: "no-store",
    });
  } catch {
    return NextResponse.json(
      { detail: "Upstream unavailable.", code: "bad_gateway" },
      { status: 502 },
    );
  }

  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") || "application/json",
    },
  });
}

/** Same-origin BFF: a new personal notebook (S-059). */
export async function POST(request: NextRequest) {
  return forwardRecipeRequest(request, { method: "POST", path: "/notebooks", withBody: true });
}
