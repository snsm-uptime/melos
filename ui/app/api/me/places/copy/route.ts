import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

/** Same-origin BFF: replace the caller's places with a copy of a member's (spec 070 FR-010a). */
export async function POST(request: NextRequest) {
  return forwardRecipeRequest(request, {
    method: "POST",
    path: "/me/places/copy",
    withBody: true,
  });
}
