"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/** At most one keep-alive per this long while the member types or selects (research R10). */
export const KEEP_ALIVE_EVERY_MS = 30_000;
/** The warning shows this long before the lock ends without activity. */
export const LOCK_WARN_MS = 60_000;

type Options = {
  /** Sends the keep-alive (the lock route, idempotent for its holder). */
  keepAlive: () => void;
  /** When my lock ends without activity (ISO-8601), or null when I hold none. */
  idleExpiresAt: string | null;
};

/**
 * Activity-only keep-alive for an edit lock (spec 022 FR-020a). Call `notifyActivity()` from
 * change handlers; a page that is merely open sends nothing, so a forgotten tab loses the lock.
 * `warning` turns on one minute before the end, `expired` once it has passed. The clock only
 * drives the display; it never sends a keep-alive.
 */
export function useLockKeepAlive({ keepAlive, idleExpiresAt }: Options) {
  const lastSent = useRef<number | null>(null);
  const [now, setNow] = useState(() => Date.now());
  const keepAliveRef = useRef(keepAlive);
  useEffect(() => {
    keepAliveRef.current = keepAlive;
  }, [keepAlive]);

  useEffect(() => {
    if (!idleExpiresAt) return;
    const timer = setInterval(() => setNow(Date.now()), 1_000);
    return () => clearInterval(timer);
  }, [idleExpiresAt]);

  const keepNow = useCallback(() => {
    lastSent.current = Date.now();
    keepAliveRef.current();
  }, []);

  const notifyActivity = useCallback(() => {
    const at = Date.now();
    if (lastSent.current !== null && at - lastSent.current < KEEP_ALIVE_EVERY_MS) return;
    lastSent.current = at;
    keepAliveRef.current();
  }, []);

  const endsAt = idleExpiresAt ? Date.parse(idleExpiresAt) : null;
  const left = endsAt === null || Number.isNaN(endsAt) ? null : endsAt - now;
  return {
    notifyActivity,
    keepNow,
    warning: left !== null && left > 0 && left <= LOCK_WARN_MS,
    expired: left !== null && left <= 0,
  };
}
