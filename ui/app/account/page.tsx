import { redirect } from "next/navigation";

import { AccountMenu } from "@/components/AccountMenu";
import { fetchSession } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Account menu — theme, password reset, sign out. (Language selection removed; UI is English-only.) */
export default async function AccountPage() {
  const session = await fetchSession();
  if (!session) {
    redirect("/sign-in?returnTo=/account");
  }

  return <AccountMenu />;
}
