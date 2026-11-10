import { CheckIcon, NotebookIcon, RecipeIcon, SendIcon, UsersIcon } from "@/app/icons";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { FakeButton, inAt, MiniCard, popAt, Scene } from "./parts";

/** Invented members: initials only, never a photo (constitution 4). */
const MEMBERS = [
  { alias: "Ana", notebook: "notebookAna" },
  { alias: "Leo", notebook: "notebookLeo" },
] as const;

/** Cook together (FR-006.3): a kitchen with two members and a recipe sent to one of them. */
export function TogetherScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.together;
  return (
    <Scene>
      <MiniCard title={t.kitchen} icon={<UsersIcon />}>
        <span className="text-[0.7rem] font-semibold uppercase tracking-[0.05em] text-muted">
          {t.members}
        </span>
        {MEMBERS.map((member, index) => (
          <div
            key={member.alias}
            className={`flex min-w-0 items-center gap-2 ${inAt(index === 0 ? 1 : 2)}`}
          >
            <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-accent-fill font-semibold text-on-accent">
              {member.alias[0]}
            </span>
            <span className="shrink-0 font-semibold">{member.alias}</span>
            <span className="flex min-w-0 items-center gap-1 text-muted">
              <NotebookIcon className="size-3.5 shrink-0" />
              <span className="truncate">{t[member.notebook]}</span>
            </span>
          </div>
        ))}
      </MiniCard>

      <MiniCard title={t.recipe} icon={<RecipeIcon />} className={inAt(3)}>
        <FakeButton className={popAt(4)}>
          <SendIcon className="size-3.5" />
          {t.send}
        </FakeButton>
      </MiniCard>

      <span
        className={`flex w-fit items-center gap-1.5 rounded-[var(--radius-md)] border border-border bg-surface px-3 py-1.5 shadow-elevation-1 ${inAt(5)}`}
      >
        <CheckIcon className="size-4 text-owed" />
        {t.sent}
      </span>
    </Scene>
  );
}
