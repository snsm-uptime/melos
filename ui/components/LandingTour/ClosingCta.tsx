import { GhostButton } from "@/components/soft-ledger/GhostButton";
import { PrimaryButton } from "@/components/soft-ledger/PrimaryButton";

import { Glows } from "./Glows";

export type ClosingCtaProps = {
  title: string;
  body: string;
  createAccount: string;
  signIn: string;
};

/** The end of the tour: the account buttons again (FR-012), over the closing glows (FR-018). */
export function ClosingCta({ title, body, createAccount, signIn }: ClosingCtaProps) {
  return (
    // Full width, so the glows (FR-018) spread behind the centred block.
    <div className="relative isolate overflow-hidden">
      <Glows place="closing" />
      <div className="mx-auto flex max-w-2xl flex-col items-center gap-3 px-page-gutter pb-20 pt-12 text-center">
        <p className="m-0 text-[1.5rem] font-semibold leading-[1.2]">{title}</p>
        <p className="m-0 text-muted leading-[1.5]">{body}</p>
        <div className="mt-2 flex flex-wrap items-center justify-center gap-3">
          <PrimaryButton href="/signup">{createAccount}</PrimaryButton>
          <GhostButton href="/sign-in">{signIn}</GhostButton>
        </div>
      </div>
    </div>
  );
}
