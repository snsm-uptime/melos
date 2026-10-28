import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ recipeId: string }> };

/** Same-origin BFF for the name check on the edit screen (spec 027, research R2). */
export async function POST(request: NextRequest, context: RouteContext) {
  const { recipeId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/recipes/${encodeURIComponent(recipeId)}/name-matches`,
    withBody: true,
  });
}
