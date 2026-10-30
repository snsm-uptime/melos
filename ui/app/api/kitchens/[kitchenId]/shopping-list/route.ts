import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ kitchenId: string }> };

/** Same-origin BFF for the kitchen's shopping list (spec 023): cookie on, status and body back. */
export async function GET(request: NextRequest, context: RouteContext) {
  const p = await context.params;
  return forwardRecipeRequest(request, {
    method: "GET",
    path: `/kitchens/${encodeURIComponent(p.kitchenId)}/shopping-list`,
  });
}
