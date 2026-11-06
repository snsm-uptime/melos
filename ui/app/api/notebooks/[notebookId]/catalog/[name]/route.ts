import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string; name: string }> };

function path(notebookId: string, name: string): string {
  return `/notebooks/${encodeURIComponent(notebookId)}/catalog/${encodeURIComponent(name)}`;
}

/** Same-origin BFF: rename a catalog name or set its language (spec 043 US2). */
export async function PATCH(request: NextRequest, context: RouteContext) {
  const { notebookId, name } = await context.params;
  return forwardRecipeRequest(request, {
    method: "PATCH",
    path: path(notebookId, name),
    withBody: true,
  });
}

/** Delete a name no recipe uses (spec 043 US3); a 204 stays empty. */
export async function DELETE(request: NextRequest, context: RouteContext) {
  const { notebookId, name } = await context.params;
  return forwardRecipeRequest(request, { method: "DELETE", path: path(notebookId, name) });
}
