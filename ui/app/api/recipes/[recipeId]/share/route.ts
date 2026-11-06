import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ recipeId: string }> };

/** Same-origin BFF for sending a recipe to a co-member (spec 071). */
export async function POST(request: NextRequest, context: RouteContext) {
  const { recipeId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/recipes/${encodeURIComponent(recipeId)}/share`,
    withBody: true,
  });
}
