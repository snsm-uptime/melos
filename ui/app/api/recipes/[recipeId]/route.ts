import { NextRequest } from "next/server";

import { forwardRecipeRequest, RECIPE_WRITE_DEADLINE_MS } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ recipeId: string }> };

/** Same-origin BFF for one recipe (spec 027): read, replace and delete. */
export async function GET(request: NextRequest, context: RouteContext) {
  const { recipeId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "GET",
    path: `/recipes/${encodeURIComponent(recipeId)}`,
  });
}

export async function PUT(request: NextRequest, context: RouteContext) {
  const { recipeId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "PUT",
    path: `/recipes/${encodeURIComponent(recipeId)}`,
    withBody: true,
    deadlineMs: RECIPE_WRITE_DEADLINE_MS,
  });
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { recipeId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "DELETE",
    path: `/recipes/${encodeURIComponent(recipeId)}`,
  });
}
