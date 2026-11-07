import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

/** Same-origin BFF: merge two names in every notebook the preview listed (spec 043 FR-002a). */
export async function POST(request: NextRequest) {
  return forwardRecipeRequest(request, {
    method: "POST",
    path: "/catalog/merge",
    withBody: true,
  });
}
