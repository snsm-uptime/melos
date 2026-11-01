"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Whether `rows` kitchen rows would overflow the list's parent, which must be positioned and
 * have no vertical padding. Counts the rows left out, so collapsing the list cannot undo itself.
 */
export function useKitchenRowsOverflow(rows: number, enabled: boolean) {
  const listRef = useRef<HTMLUListElement>(null);
  const [overflowing, setOverflowing] = useState(false);

  useEffect(() => {
    const list = listRef.current;
    const scroller = list?.parentElement;
    if (!enabled || !list || !scroller) return;
    // A new observer reports once straight away, which covers a change in `rows`.
    const observer = new ResizeObserver(() => {
      const row = list.firstElementChild as HTMLElement | null;
      const gap = parseFloat(getComputedStyle(list).rowGap) || 0;
      const leftOut = rows - list.children.length;
      const needed =
        list.offsetTop + list.offsetHeight + leftOut * ((row?.offsetHeight ?? 0) + gap);
      setOverflowing(needed > scroller.clientHeight);
    });
    observer.observe(list);
    observer.observe(scroller);
    return () => observer.disconnect();
  }, [rows, enabled]);

  return { listRef, overflowing: enabled && overflowing };
}
