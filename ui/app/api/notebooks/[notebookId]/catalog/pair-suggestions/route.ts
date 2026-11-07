import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string }> };

/** Same-origin BFF: likely English and Spanish pairs of the catalog (spec 043 US5). */
export async function POST(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/notebooks/${encodeURIComponent(notebookId)}/catalog/pair-suggestions`,
  });
}
