import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

/** Same-origin BFF: what a merge would change, before anything does (spec 043 FR-004). */
export async function POST(request: NextRequest) {
  return forwardRecipeRequest(request, {
    method: "POST",
    path: "/catalog/merge-preview",
    withBody: true,
  });
}
