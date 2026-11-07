import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string }> };

/** Same-origin BFF: one notebook's catalog with its other names (spec 043). */
export async function GET(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "GET",
    path: `/notebooks/${encodeURIComponent(notebookId)}/catalog`,
  });
}
