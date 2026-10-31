import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ kitchenId: string }> };

/** Same-origin BFF: add an item to the kitchen's list by hand (spec 025). */
export async function POST(request: NextRequest, context: RouteContext) {
  const p = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/kitchens/${encodeURIComponent(p.kitchenId)}/shopping-list/items`,
    withBody: true,
  });
}
