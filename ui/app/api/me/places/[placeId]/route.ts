import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

type RouteContext = { params: Promise<{ placeId: string }> };

/** Same-origin BFF: rename or delete one of the caller's places (spec 070). */
export async function PATCH(request: NextRequest, context: RouteContext) {
  const { placeId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "PATCH",
    path: `/me/places/${encodeURIComponent(placeId)}`,
    withBody: true,
  });
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  const { placeId } = await context.params;
  return forwardRecipeRequest(request, {
    method: "DELETE",
    path: `/me/places/${encodeURIComponent(placeId)}`,
  });
}
