import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

/** Same-origin BFF: browser → ui /api/side-panel/default-kitchen → api. */
export async function PUT(request: NextRequest) {
  let body: { kitchen_id?: unknown };
  try {
    body = (await request.json()) as { kitchen_id?: unknown };
  } catch {
    return NextResponse.json(
      { detail: "Invalid JSON body.", code: "invalid_body" },
      { status: 400 },
    );
  }

  const headers = new Headers({ Accept: "application/json", "Content-Type": "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);
  let upstream: Response;
  try {
    upstream = await fetch(`${getApiInternalUrl()}/side-panel/default-kitchen`, {
      method: "PUT",
      headers,
      body: JSON.stringify({ kitchen_id: body.kitchen_id }),
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
