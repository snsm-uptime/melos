import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

/**
 * Same-origin BFF: /api/notebooks/default → api /notebooks/default (created on first use).
 */
export async function GET(request: NextRequest) {
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let upstream: Response;
  try {
    upstream = await fetch(`${getApiInternalUrl()}/notebooks/default`, {
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

/** Makes one of the caller's personal notebooks their default: api PUT /notebooks/default. */
export async function PUT(request: NextRequest) {
  let body: { notebook_id?: unknown };
  try {
    body = (await request.json()) as { notebook_id?: unknown };
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
    upstream = await fetch(`${getApiInternalUrl()}/notebooks/default`, {
      method: "PUT",
      headers,
      body: JSON.stringify({ notebook_id: body.notebook_id }),
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
