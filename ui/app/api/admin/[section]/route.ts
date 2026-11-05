import { NextRequest, NextResponse } from "next/server";

import { getApiInternalUrl } from "@/lib/api";

const SECTIONS = new Set(["units", "ingredients", "recipes", "users", "refused-sites"]);

type RouteContext = { params: Promise<{ section: string }> };

/** Same-origin BFF: the dashboard sections and nothing else (specs 055, 067 contracts/admin-api). */
export async function GET(request: NextRequest, context: RouteContext) {
  const { section } = await context.params;
  if (!SECTIONS.has(section)) {
    return NextResponse.json({ detail: "Not Found" }, { status: 404 });
  }
  const headers = new Headers({ Accept: "application/json" });
  const cookie = request.headers.get("cookie");
  if (cookie) headers.set("Cookie", cookie);

  let upstream: Response;
  try {
    upstream = await fetch(`${getApiInternalUrl()}/admin/${section}`, {
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
