import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";
import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = {
  params: Promise<{ notebookId: string }>;
};

/**
 * Same-origin BFF: /api/notebooks/{id} → api /notebooks/{id}.
 */
export async function GET(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let upstream: Response;
  try {
    upstream = await fetch(
      `${getApiInternalUrl()}/notebooks/${encodeURIComponent(notebookId)}`,
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

/** Renames a notebook (spec 059). */
export async function PATCH(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "PATCH",
    path: `/notebooks/${encodeURIComponent(notebookId)}`,
    withBody: true,
  });
}

/** Deletes a notebook; a 204 passes through with no body (spec 059). */
export async function DELETE(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "DELETE",
    path: `/notebooks/${encodeURIComponent(notebookId)}`,
  });
}
