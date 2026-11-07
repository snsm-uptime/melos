import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string }> };

/** Same-origin BFF: remember that a suggested pair is not one ingredient (spec 043 FR-009d). */
export async function POST(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/notebooks/${encodeURIComponent(notebookId)}/catalog/pair-dismissals`,
    withBody: true,
  });
}
