import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

/** Same-origin BFF: browser → ui /api/side-panel → api /side-panel. */
export async function GET(request: NextRequest) {
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);
  let upstream: Response;
  try {
    upstream = await fetch(`${getApiInternalUrl()}/side-panel`, {
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
      "Content-Type": upstream.headers.get("Content-Type") || "application/json",
    },
  });
}
