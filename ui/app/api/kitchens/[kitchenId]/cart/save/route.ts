import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ kitchenId: string }> };

/** Same-origin BFF for the kitchen cart and edit locks (spec 022): cookie on, status and body back. */
export async function POST(request: NextRequest, context: RouteContext) {
  const p = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/kitchens/${encodeURIComponent(p.kitchenId)}/cart/save`,
  });
}
