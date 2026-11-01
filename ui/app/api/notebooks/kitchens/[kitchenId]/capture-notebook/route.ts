import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

type RouteContext = {
  params: Promise<{ kitchenId: string }>;
};

/**
 * Same-origin BFF: /api/notebooks/kitchens/{id}/capture-notebook → api
 * /notebooks/kitchens/{id}/capture-notebook (spec 035 research R6).
 */
export async function POST(request: NextRequest, context: RouteContext) {
  const { kitchenId } = await context.params;
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let upstream: Response;
  try {
    upstream = await fetch(
      `${getApiInternalUrl()}/notebooks/kitchens/${encodeURIComponent(kitchenId)}/capture-notebook`,
      { method: "POST", headers, cache: "no-store" },
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
      "Content-Type": upstream.headers.get("Content-Type") || "application/json",
    },
  });
}
