"use client";

import { useCallback, useSyncExternalStore } from "react";

export const SIDE_PANEL_KEY = "melos_side_panel_open";

const listeners = new Set<() => void>();

function subscribe(onChange: () => void): () => void {
  listeners.add(onChange);
  return () => {
    listeners.delete(onChange);
  };
}

function readOpen(): boolean {
  try {
    return window.localStorage.getItem(SIDE_PANEL_KEY) === "true";
  } catch {
    return false;
  }
}

/** Open or closed on this device, larger screens only. Closed until the browser can read it. */
export function useSidePanelState(): { isOpen: boolean; setOpen: (open: boolean) => void } {
  const isOpen = useSyncExternalStore(subscribe, readOpen, () => false);
  const setOpen = useCallback((open: boolean) => {
    try {
      window.localStorage.setItem(SIDE_PANEL_KEY, String(open));
    } catch {
      // Private browsing can refuse storage; the panel then just forgets.
    }
    for (const listener of listeners) listener();
  }, []);
  return { isOpen, setOpen };
}
