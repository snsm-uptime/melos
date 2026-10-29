"use client";

import type { Locale } from "@/lib/i18n/locale";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

import { RowControls } from "./RowControls";

type EditableStepCardProps = {
  index: number;
  count: number;
  text: string;
  onChange: (text: string) => void;
  onRemove: () => void;
  onMove: (direction: -1 | 1) => void;
  readOnly?: false;
  locale?: Locale;
};

type ReadOnlyStepCardProps = {
  index: number;
  text: string;
  /** Display only: the step is text, with no field and no row controls (spec 027). */
  readOnly: true;
  locale?: Locale;
};

export type StepCardProps = EditableStepCardProps | ReadOnlyStepCardProps;

/** A big bold step number, centred on the step. */
const numberClassName =
  "min-w-8 shrink-0 text-[1.75rem] font-bold leading-none tabular-nums text-accent";

/** Steps are separated by dividers, not cards: a hairline between rows, none after the last. */
const rowClassName = "flex min-h-16 min-w-0 items-center gap-3 border-b border-border py-3 last:border-b-0";

/** One step of a recipe: numbered, to edit (draft, edit) or display only (detail). */
export function StepCard(props: StepCardProps) {
  const { index, text } = props;
  const t = useCaptureMessages(props.locale);
  if (props.readOnly) {
    return (
      <li className={rowClassName}>
        <span aria-hidden="true" className={numberClassName}>
          {index + 1}
        </span>
        <p className="m-0 min-w-0 flex-1 whitespace-pre-wrap px-1 py-[0.15rem] text-[0.95rem] text-foreground">
          {text}
        </p>
      </li>
    );
  }
  return (
    <li className={rowClassName}>
      <span aria-hidden="true" className={numberClassName}>
        {index + 1}
      </span>
      <textarea
        aria-label={t.stepLabel(index + 1)}
        rows={1}
        className="min-w-0 flex-1 field-sizing-content resize-none rounded-[0.4rem] border-0 bg-transparent px-1 py-[0.15rem] text-[0.95rem] text-foreground outline-none hover:bg-background focus:bg-background"
        value={text}
        onChange={(event) => props.onChange(event.target.value)}
      />
      <RowControls
        divider={false}
        index={index}
        count={props.count}
        onRemove={props.onRemove}
        onMove={props.onMove}
        locale={props.locale}
      />
    </li>
  );
}
