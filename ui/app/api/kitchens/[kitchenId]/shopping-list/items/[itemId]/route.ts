import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ kitchenId: string; itemId: string }> };

/** Same-origin BFF: remove an item added by hand (spec 025). */
export async function DELETE(request: NextRequest, context: RouteContext) {
  const p = await context.params;
  return forwardRecipeRequest(request, {
    method: "DELETE",
    path: `/kitchens/${encodeURIComponent(p.kitchenId)}/shopping-list/items/${encodeURIComponent(p.itemId)}`,
  });
}

/** Same-origin BFF: mark an item bought or not bought (spec 070 FR-001). */
export async function PATCH(request: NextRequest, context: RouteContext) {
  const p = await context.params;
  return forwardRecipeRequest(request, {
    method: "PATCH",
    path: `/kitchens/${encodeURIComponent(p.kitchenId)}/shopping-list/items/${encodeURIComponent(p.itemId)}`,
    withBody: true,
  });
}
