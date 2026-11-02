import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string }> };

/** Same-origin BFF: a member leaves the notebook (spec 057). */
export async function DELETE(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "DELETE",
    path: `/notebooks/${encodeURIComponent(notebookId)}/members/me`,
  });
}
