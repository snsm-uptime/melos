import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ kitchenId: string }> };

/** Same-origin BFF: Done closes the kitchen's active list (spec 025). */
export async function POST(request: NextRequest, context: RouteContext) {
  const p = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/kitchens/${encodeURIComponent(p.kitchenId)}/shopping-list/done`,
    withBody: true,
  });
}
