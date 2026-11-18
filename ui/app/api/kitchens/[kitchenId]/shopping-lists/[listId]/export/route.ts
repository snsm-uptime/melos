import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ kitchenId: string; listId: string }> };

/** Same-origin BFF: the Markdown copy or the PDF of one shopping list (spec 024). */
export async function GET(request: NextRequest, context: RouteContext) {
  const p = await context.params;
  const format = request.nextUrl.searchParams.get("format") ?? "";
  return forwardRecipeRequest(request, {
    method: "GET",
    path: `/kitchens/${encodeURIComponent(p.kitchenId)}/shopping-lists/${encodeURIComponent(p.listId)}/export?format=${encodeURIComponent(format)}`,
  });
}
