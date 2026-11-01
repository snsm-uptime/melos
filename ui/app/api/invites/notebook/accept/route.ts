/** Same-origin BFF: join a notebook from its emailed link (spec 057). */

import { NextRequest } from "next/server";

import { forwardRecipeRequest } from "@/lib/recipeBff";

export async function POST(request: NextRequest) {
  return forwardRecipeRequest(request, {
    method: "POST",
    path: "/invites/notebook/accept",
    withBody: true,
  });
}
