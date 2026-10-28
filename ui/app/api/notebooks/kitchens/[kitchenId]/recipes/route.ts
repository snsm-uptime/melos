import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

type RouteContext = {
  params: Promise<{ kitchenId: string }>;
};

/** Same-origin BFF for a recipe list (spec 021): forwards page, q and the session cookie. */
export async function GET(request: NextRequest, context: RouteContext) {
  const { kitchenId } = await context.params;
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  const incoming = new URL(request.url).searchParams;
  const forwarded = new URLSearchParams();
  for (const key of ["page", "q"]) {
    const value = incoming.get(key);
    if (value !== null) forwarded.set(key, value);
  }
  const suffix = forwarded.size > 0 ? `?${forwarded.toString()}` : "";

  let upstream: Response;
  try {
    upstream = await fetch(`${getApiInternalUrl()}/notebooks/kitchens/${encodeURIComponent(kitchenId)}/recipes${suffix}`, {
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
