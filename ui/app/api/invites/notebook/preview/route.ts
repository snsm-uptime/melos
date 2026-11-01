/** Same-origin BFF: public preview of a notebook invite (spec 057). */

import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

export async function GET(request: NextRequest) {
  const query = new URLSearchParams({ token: request.nextUrl.searchParams.get("token") ?? "" });
  return forwardRecipeRequest(request, {
    method: "GET",
    path: `/invites/notebook/preview?${query}`,
  });
}
