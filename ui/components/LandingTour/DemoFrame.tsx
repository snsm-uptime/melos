"use client";

import { useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from "react";

import type { DemoId } from "@/lib/i18n/landing";

import styles from "./DemoFrame.module.scss";

/** Share of the frame that must be on screen for its demo to play (research R3). */
const IN_VIEW_RATIO = 0.35;
const REDUCED_MOTION = "(prefers-reduced-motion: reduce)";

function subscribeReducedMotion(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => {};
  const query = window.matchMedia(REDUCED_MOTION);
  query.addEventListener("change", onChange);
  return () => query.removeEventListener("change", onChange);
}

function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(REDUCED_MOTION).matches;
}

export type DemoFrameProps = {
  id: DemoId;
  /** Labels the demo for screen readers. */
  title: string;
  /** What the demo shows, read by screen readers instead of the moving scene (FR-009). */
  description: string;
  pauseLabel: string;
  playLabel: string;
  /** The server-rendered scene. Its resting style is its final state. */
  children: ReactNode;
};

/**
 * Plays a landing demo only while it is in view, with a pause button (FR-007). The scene's
 * animations run once `data-started` is "true" and freeze in place while `data-playing` is "false"
 * (scenes.module.scss). Before hydration, without IntersectionObserver or under reduced motion,
 * nothing runs and the scene shows its final state.
 */
export function DemoFrame({ id, title, description, pauseLabel, playLabel, children }: DemoFrameProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);
  const [started, setStarted] = useState(false);
  const [userPaused, setUserPaused] = useState(false);
  // On the server, as under reduced motion: no button, since nothing moves yet.
  const reducedMotion = useSyncExternalStore(subscribeReducedMotion, prefersReducedMotion, () => true);

  useEffect(() => {
    const element = ref.current;
    if (!element || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          const visible = Boolean(entry.isIntersecting) && entry.intersectionRatio >= IN_VIEW_RATIO;
          setInView(visible);
          if (visible) setStarted(true);
        }
      },
      { threshold: IN_VIEW_RATIO },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const playing = inView && !userPaused;

  return (
    <div
      ref={ref}
      role="group"
      aria-label={title}
      data-demo={id}
      data-started={started ? "true" : "false"}
      data-playing={playing ? "true" : "false"}
      className={styles.frame}
    >
      {/* The scene is the app's own components: inert, so none of their controls can be reached. */}
      <div aria-hidden="true" inert className={styles.scene}>
        {children}
      </div>
      <p className="sr-only">{description}</p>
      {reducedMotion ? null : (
        <button
          type="button"
          aria-pressed={userPaused}
          aria-label={userPaused ? playLabel : pauseLabel}
          title={userPaused ? playLabel : pauseLabel}
          onClick={() => setUserPaused((paused) => !paused)}
          className={styles.control}
        >
          <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
            {userPaused ? (
              <path d="M8 5.5v13l10.5-6.5Z" fill="currentColor" />
            ) : (
              <path d="M8 5.5v13M16 5.5v13" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
            )}
          </svg>
        </button>
      )}
    </div>
  );
}
