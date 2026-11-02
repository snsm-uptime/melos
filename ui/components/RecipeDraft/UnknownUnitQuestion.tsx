"use client";

import { customUnitMessages } from "@/lib/i18n/customUnits";
import type { Locale } from "@/lib/i18n/locale";
import { useLocale } from "@/lib/i18n/useLocale";

type UnknownUnitQuestionProps = {
  /** The words to ask about, as stored: a unit reads the same in every language (FR-015). */
  words: string[];
  onAnswer: (word: string, keep: boolean) => void;
  /** The language of the screen; the provider's language when not given. */
  locale?: Locale;
};

const answerClassName =
  "min-h-10 min-w-16 rounded-[0.75rem] border border-border bg-background px-3 py-1 text-[0.9rem] text-foreground hover:bg-card";

/** One question per word a line uses and the person has not answered (spec 055 FR-004). */
export function UnknownUnitQuestion({ words, onAnswer, locale }: UnknownUnitQuestionProps) {
  const providerLocale = useLocale();
  const t = customUnitMessages[locale ?? providerLocale];
  if (words.length === 0) return null;
  return (
    <ul className="m-0 flex list-none flex-col gap-2 p-0">
      {words.map((word) => (
        <li
          key={word}
          data-unit-question={word}
          className="flex flex-wrap items-center justify-between gap-2 rounded-[0.75rem] border border-accent px-3 py-2"
        >
          <p className="m-0 min-w-0 text-[0.9rem] text-foreground">{t.question(word)}</p>
          <div className="flex shrink-0 gap-2">
            <button type="button" className={answerClassName} onClick={() => onAnswer(word, true)}>
              {t.yes}
            </button>
            <button type="button" className={answerClassName} onClick={() => onAnswer(word, false)}>
              {t.no}
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}
