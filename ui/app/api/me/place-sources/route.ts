import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

/** Same-origin BFF: members the caller can copy places from (spec 070 R8). */
export async function GET(request: NextRequest) {
  return forwardRecipeRequest(request, { method: "GET", path: "/me/place-sources" });
}
