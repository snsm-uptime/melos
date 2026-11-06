import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

/** Same-origin BFF: the caller's places (spec 070 contracts/places.md). */
export async function GET(request: NextRequest) {
  return forwardRecipeRequest(request, { method: "GET", path: "/me/places" });
}

export async function POST(request: NextRequest) {
  return forwardRecipeRequest(request, { method: "POST", path: "/me/places", withBody: true });
}
