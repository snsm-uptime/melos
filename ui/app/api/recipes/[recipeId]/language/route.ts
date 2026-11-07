import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ recipeId: string }> };

/** Same-origin BFF: apply or dismiss a recipe's detected language (spec 043 FR-005a). */
export async function PATCH(request: NextRequest, context: RouteContext) {
  const { recipeId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "PATCH",
    path: `/recipes/${encodeURIComponent(recipeId)}/language`,
    withBody: true,
  });
}
