import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string; inviteId: string }> };

/** Same-origin BFF: the owner cancels an invite (spec 057). */
export async function DELETE(request: NextRequest, context: RouteContext) {
  const { notebookId, inviteId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "DELETE",
    path: `/notebooks/${encodeURIComponent(notebookId)}/invites/${encodeURIComponent(inviteId)}`,
  });
}
