import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string; userId: string }> };

/** Same-origin BFF: the owner removes a member (spec 057). */
export async function DELETE(request: NextRequest, context: RouteContext) {
  const { notebookId, userId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "DELETE",
    path: `/notebooks/${encodeURIComponent(notebookId)}/members/${encodeURIComponent(userId)}`,
  });
}
