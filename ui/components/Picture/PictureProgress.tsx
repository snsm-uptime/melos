"use client";

import { useEffect, useMemo, useState } from "react";

import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

/**
 * The steps of a picture capture, in order (spec 041, FR-027 progress, research R9). The api
 * does not stream its progress, so the bar follows a fixed sequence over the expected total;
 * the upload step is the only one that could be measured, and it is shown on the same sequence.
 */
export const PICTURE_STEPS = [
  { key: "upload", ms: 1_000 },
  { key: "prepare", ms: 1_000 },
  { key: "identify", ms: 1_000 },
  { key: "compress", ms: 2_000 },
  { key: "read", ms: 12_000 },
  { key: "draft", ms: 4_000 },
] as const;

/** The bar never reaches the end until the answer does. */
const CAP = 0.95;

/** Where the bar is `elapsedMs` after the submission began: a step index and the share of it. */
export function progressAt(elapsedMs: number): { fraction: number; step: string } {
  const total = PICTURE_STEPS.reduce((sum, step) => sum + step.ms, 0);
  let remaining = Math.max(0, elapsedMs);
  let done = 0;
  for (const step of PICTURE_STEPS) {
    if (remaining < step.ms) {
      return { fraction: Math.min(CAP, (done + remaining) / total), step: step.key };
    }
    remaining -= step.ms;
    done += step.ms;
  }
  return { fraction: CAP, step: "draft" };
}

/** One phrase, picked at random once per submission (FR-027). */
export function pickPhrase(
  phrases: readonly string[],
  handwrittenPhrase: string,
  handwritten: boolean,
  random: () => number = Math.random,
): string {
  if (handwritten) return handwrittenPhrase;
  return phrases[Math.floor(random() * phrases.length)] ?? phrases[0];
}

type PictureProgressProps = { handwritten: boolean };

/** A thin bar and one phrase over it, shown while a picture is read. */
export function PictureProgress({ handwritten }: PictureProgressProps) {
  const t = useCaptureMessages();
  const phrase = useMemo(
    () => pickPhrase(t.progressPhrases, t.progressHandwrittenPhrase, handwritten),
    // Once per submission: the phrase does not change while the bar moves.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = setInterval(() => setElapsed(Date.now() - started), 200);
    return () => clearInterval(timer);
  }, []);

  const { fraction } = progressAt(elapsed);
  return (
    <div className="flex flex-col gap-2" role="status" aria-live="polite">
      <p className="m-0 text-[0.9rem] text-muted">{phrase}</p>
      <div
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(fraction * 100)}
        className="h-1 w-full overflow-hidden rounded-full bg-field-border"
      >
        <div
          className="h-full bg-primary transition-[width] duration-200"
          style={{ width: `${Math.round(fraction * 100)}%` }}
        />
      </div>
    </div>
  );
}
