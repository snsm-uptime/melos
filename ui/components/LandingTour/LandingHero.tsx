import type { ReactNode } from "react";

import { CauldronMark } from "@/components/CauldronLoader";
import { GhostButton } from "@/components/soft-ledger/GhostButton";
import { PrimaryButton } from "@/components/soft-ledger/PrimaryButton";

export type LandingHeroProps = {
  headline: string;
  intro: string;
  createAccount: string;
  signIn: string;
  /** The overview demo (FR-002a); in view on load, so it plays without scrolling. */
  demo?: ReactNode;
};

/** The top of the signed-out page: name, headline, intro, account buttons and the overview demo. */
export function LandingHero({ headline, intro, createAccount, signIn, demo }: LandingHeroProps) {
  return (
    <section className="relative overflow-hidden">
      <svg
        aria-hidden="true"
        viewBox="0 0 1440 400"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-0 -z-10 h-full w-full"
      >
        <path
          d="M0,260 C240,330 480,200 720,260 C960,320 1200,220 1440,280 L1440,340 C1200,270 960,370 720,310 C480,250 240,350 0,300 Z"
          className="fill-accent/[0.06]"
        />
        <path
          d="M0,300 C240,350 480,250 720,310 C960,370 1200,270 1440,340 C1200,396.67 960,283.33 720,330 C480,376.67 240,263.33 0,300 Z"
          className="fill-accent/10"
        />
      </svg>
      <div className="mx-auto grid max-w-5xl grid-cols-1 items-center gap-10 px-page-gutter pb-16 pt-20 md:grid-cols-2">
        <div className="flex min-w-0 flex-col items-center gap-4 text-center md:items-start md:text-left">
          <h1 className="m-0 flex flex-col items-center gap-3 md:items-start">
            <span className="flex items-center gap-2 text-[1.5rem] font-semibold leading-[1.15]">
              <CauldronMark className="size-[1.25em] shrink-0" />
              Melos
            </span>
            <span className="text-[2rem] font-semibold leading-[1.15] text-balance">{headline}</span>
          </h1>
          <p className="m-0 max-w-lg text-muted leading-[1.5]">{intro}</p>
          <div className="mt-2 flex flex-wrap items-center justify-center gap-3 md:justify-start">
            <PrimaryButton href="/signup">{createAccount}</PrimaryButton>
            <GhostButton href="/sign-in">{signIn}</GhostButton>
          </div>
        </div>
        {demo ? <div className="min-w-0">{demo}</div> : null}
      </div>
    </section>
  );
}
