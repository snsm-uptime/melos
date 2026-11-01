import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ notebookId: string }> };

function path(notebookId: string): string {
  return `/notebooks/${encodeURIComponent(notebookId)}/invites`;
}

/** Same-origin BFF: the owner's list of a notebook's invites (spec 057). */
export async function GET(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;
  return forwardRecipeRequest(request, { method: "GET", path: path(notebookId) });
}

/** Same-origin BFF: the owner invites an email. */
export async function POST(request: NextRequest, context: RouteContext) {
  const { notebookId } = await context.params;
  return forwardRecipeRequest(request, { method: "POST", path: path(notebookId), withBody: true });
}
