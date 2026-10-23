import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

type RouteContext = {
  params: Promise<{ userId: string }>;
};

/**
 * Same-origin BFF: /api/notebooks/members/{userId} → api /notebooks/members/{userId}.
 * Returns the member's default notebook; the api creates it on first use.
 */
export async function GET(request: NextRequest, context: RouteContext) {
  const { userId } = await context.params;
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let upstream: Response;
  try {
    upstream = await fetch(
      `${getApiInternalUrl()}/notebooks/members/${encodeURIComponent(userId)}`,
      { method: "GET", headers, cache: "no-store" },
    );
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
