import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

/** Same-origin BFF: the caller's place per ingredient (spec 070 contracts/places.md). */
export async function GET(request: NextRequest) {
  return forwardRecipeRequest(request, { method: "GET", path: "/me/ingredient-places" });
}

export async function PUT(request: NextRequest) {
  return forwardRecipeRequest(request, {
    method: "PUT",
    path: "/me/ingredient-places",
    withBody: true,
  });
}
