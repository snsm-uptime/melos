import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string; inviteId: string }> };

/** Same-origin BFF: the owner resends an open or expired invite (spec 057). */
export async function POST(request: NextRequest, context: RouteContext) {
  const { notebookId, inviteId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "POST",
    path: `/notebooks/${encodeURIComponent(notebookId)}/invites/${encodeURIComponent(inviteId)}/resend`,
  });
}
