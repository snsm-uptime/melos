import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = {
  params: Promise<{ kitchenId: string; recipeId: string }>;
};

/** Same-origin BFF for the kitchen cart and edit locks (spec 022): cookie on, status and body back. */
export async function DELETE(request: NextRequest, context: RouteContext) {
  const p = await context.params;
  return forwardRecipeRequest(request, {
    method: "DELETE",
    path: `/kitchens/${encodeURIComponent(p.kitchenId)}/cart/draft/items/${encodeURIComponent(p.recipeId)}`,
  });
}
