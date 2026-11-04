import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

type RouteContext = { params: Promise<{ recipeId: string }> };

/** Same-origin BFF for the admin's recipe delete (spec 055, admin-api). Other writes do not exist. */
export async function DELETE(request: NextRequest, context: RouteContext) {
  const { recipeId } = await context.params;
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let upstream: Response;
  try {
    upstream = await fetch(
      `${getApiInternalUrl()}/admin/recipes/${encodeURIComponent(recipeId)}`,
      { method: "DELETE", headers, cache: "no-store" },
    );
  } catch {
    return NextResponse.json(
      { detail: "Upstream unavailable.", code: "bad_gateway" },
      { status: 502 },
    );
  }

  if (upstream.status === 204) return new NextResponse(null, { status: 204 });
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") || "application/json",
    },
  });
}
