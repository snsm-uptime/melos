import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ kitchenId: string; listId: string }> };

/** Same-origin BFF: one closed list (spec 025). */
export async function GET(request: NextRequest, context: RouteContext) {
  const p = await context.params;
  return forwardRecipeRequest(request, {
    method: "GET",
    path: `/kitchens/${encodeURIComponent(p.kitchenId)}/shopping-lists/${encodeURIComponent(p.listId)}`,
  });
}
