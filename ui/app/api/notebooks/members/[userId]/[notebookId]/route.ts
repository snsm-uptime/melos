import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

type RouteContext = {
  params: Promise<{ userId: string; notebookId: string }>;
};

/**
 * Same-origin BFF: /api/notebooks/members/{userId}/{notebookId}
 * → api /notebooks/members/{userId}/{notebookId}.
 */
export async function GET(request: NextRequest, context: RouteContext) {
  const { userId, notebookId } = await context.params;
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let upstream: Response;
  try {
    upstream = await fetch(
      `${getApiInternalUrl()}/notebooks/members/${encodeURIComponent(userId)}/${encodeURIComponent(notebookId)}`,
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
