"use client";

import type { CSSProperties } from "react";

import { loaderMessages } from "@/lib/i18n/loader";
import { useLocale } from "@/lib/i18n/useLocale";

import styles from "./CauldronLoader.module.scss";
import {
  ASPECT_RATIO,
  BUBBLES,
  CAULDRON_SHAPES,
  PIVOT,
  VIEWBOX_ATTR,
} from "./geometry";
import {
  CAULDRON_TILT_DEFAULT,
  CAULDRON_TILT_IN_BUTTON,
  resolveTilt,
} from "./tilt";

export type CauldronLoaderProps = {
  /** `page` for a screen or panel; `button` inside a button or a header action. */
  tone?: "page" | "button";
  /** Degrees each way. 0 to 45, sign ignored; anything else takes the tone's default. */
  tilt?: number;
  /** CSS length. Page tone: the width. Button tone: the height, so a button never grows. */
  size?: string;
  /** Screen-reader text, for a message more specific than "Loading". */
  label?: string;
  /** Placement only (margin, padding). Page tone puts it on the centring stage around the loader. */
  className?: string;
};

/**
 * The one loading indicator (spec 065): a cauldron that rocks while bubbles rise. Drawn in inline
 * SVG and animated with CSS alone, so it needs no request and no timer.
 */
export function CauldronLoader({
  tone = "page",
  tilt,
  size,
  label,
  className,
}: CauldronLoaderProps) {
  const locale = useLocale();
  const isButton = tone === "button";
  const degrees = resolveTilt(
    tilt,
    isButton ? CAULDRON_TILT_IN_BUTTON : CAULDRON_TILT_DEFAULT,
  );

  const style: CSSProperties & Record<"--cauldron-tilt", string> = {
    "--cauldron-tilt": `${degrees}deg`,
    aspectRatio: ASPECT_RATIO,
    ...(isButton ? { height: size ?? "1.2em" } : { width: size ?? "3rem" }),
  };

  // In a button the children are presentational, so a nested status would not be announced; the
  // hidden text joins the button's name and its own aria-busy is the signal (research R9).
  const live = isButton ? {} : { role: "status", "aria-live": "polite" as const };
  const rootClass = [styles.root, isButton ? styles.button : styles.page, isButton && className]
    .filter(Boolean)
    .join(" ");

  const loader = (
    <span {...live} className={rootClass} style={style}>
      <svg
        className={styles.svg}
        viewBox={VIEWBOX_ATTR}
        aria-hidden="true"
        focusable="false"
      >
        <g className={styles.bubbles}>
          {BUBBLES.map(({ cx, cy, r }, index) => (
            <circle
              key={index}
              className={styles.bubble}
              data-bubble={index}
              cx={cx}
              cy={cy}
              r={r}
            />
          ))}
        </g>
        <g
          className={styles.cauldron}
          style={{ transformOrigin: `${PIVOT.x}px ${PIVOT.y}px` }}
        >
          <path data-part="body" className={styles.body} d={CAULDRON_SHAPES.body.d} />
          <path data-part="rim" className={styles.drip} d={CAULDRON_SHAPES.rim.d} />
          <path data-part="handle" className={styles.body} d={CAULDRON_SHAPES.handleLeft.d} />
          <path data-part="handle" className={styles.body} d={CAULDRON_SHAPES.handleRight.d} />
          <path data-part="foot" className={styles.body} d={CAULDRON_SHAPES.footLeft.d} />
          <path data-part="foot" className={styles.body} d={CAULDRON_SHAPES.footRight.d} />
          <path data-part="drip" className={styles.drip} d={CAULDRON_SHAPES.drip.d} />
        </g>
      </svg>
      <span className="sr-only">{label ?? loaderMessages[locale].loading}</span>
    </span>
  );

  if (isButton) return loader;
  return <div className={[styles.stage, className].filter(Boolean).join(" ")}>{loader}</div>;
}
