import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";
import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = {
  params: Promise<{ kitchenId: string }>;
};

/**
 * Same-origin BFF: /api/notebooks/kitchens/{id} → api /notebooks/kitchens/{id}.
 */
export async function GET(request: NextRequest, context: RouteContext) {
  const { kitchenId } = await context.params;
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let upstream: Response;
  try {
    upstream = await fetch(
      `${getApiInternalUrl()}/notebooks/kitchens/${encodeURIComponent(kitchenId)}`,
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

/** Adds an empty kitchen notebook (spec 059). */
export async function POST(request: NextRequest, context: RouteContext) {
  const { kitchenId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/notebooks/kitchens/${encodeURIComponent(kitchenId)}`,
    withBody: true,
  });
}
