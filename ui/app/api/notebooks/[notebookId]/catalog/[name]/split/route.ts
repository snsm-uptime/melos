import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string; name: string }> };

/** Same-origin BFF: split an other name back out into its own ingredient (spec 043 US4). */
export async function POST(request: NextRequest, context: RouteContext) {
  const { notebookId, name } = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/notebooks/${encodeURIComponent(notebookId)}/catalog/${encodeURIComponent(name)}/split`,
    withBody: true,
  });
}
