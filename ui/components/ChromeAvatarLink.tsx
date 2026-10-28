"use client";

import Link from "next/link";

import { Avatar } from "@/components/Avatar";
import { accountCopy } from "@/lib/i18n/account";
import { useLocale } from "@/lib/i18n/useLocale";

/**
 * Chrome leading-slot avatar for top-level tab roots (chrome-header spec):
 * a real link to /account, not a decorative image — gains the app-standard
 * focus/hover outline so the affordance matches the interaction it performs.
 */
export function ChromeAvatarLink({
  alias,
  userId,
  photoBase64,
}: {
  alias: string | null;
  userId: string;
  photoBase64: string | null;
}) {
  const t = accountCopy(useLocale());
  return (
    <Link
      href="/account"
      aria-label={t.goToAccount}
      className="inline-flex rounded-[8px] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent hover:outline hover:outline-2 hover:outline-offset-2 hover:outline-accent"
    >
      <Avatar alias={alias} seed={userId} photoBase64={photoBase64} size="md" />
    </Link>
  );
}
