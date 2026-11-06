import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

/** Same-origin BFF for the people a recipe can be shared with (spec 071). */
export async function GET(request: NextRequest) {
  return forwardRecipeRequest(request, {
    method: "GET",
    path: "/recipes/share-candidates",
  });
}
