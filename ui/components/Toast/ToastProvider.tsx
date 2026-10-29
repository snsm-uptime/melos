"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

/** How long a toast that is not persistent stays (spec 022 Assumptions). */
export const TOAST_MS = 4_000;

export type Toast = {
  /** A toast shown with an id already on screen replaces it. */
  id: string;
  text: string;
  action?: { label: string; onClick: () => void };
  /** Stays until dismissed or replaced (the idle warning). */
  persistent?: boolean;
};

type ToastApi = {
  show: (toast: Toast) => void;
  dismiss: (id: string) => void;
};

type ToastState = {
  toasts: Toast[];
  dock: ReactNode;
  setDock: (owner: symbol, node: ReactNode | null) => void;
} & ToastApi;

const ToastContext = createContext<ToastState | null>(null);

const NO_OP: ToastApi = { show: () => {}, dismiss: () => {} };

/**
 * Toasts and one persistent dock above the tab bar (spec 022 research R13). `AppShell` mounts
 * the provider and the viewport; pages call `useToast()` and `useToastDock()`.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [dock, setDockState] = useState<{ owner: symbol; node: ReactNode } | null>(null);
  const timers = useRef(new Map<string, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: string) => {
    const timer = timers.current.get(id);
    if (timer) clearTimeout(timer);
    timers.current.delete(id);
    setToasts((list) => list.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback(
    (toast: Toast) => {
      const old = timers.current.get(toast.id);
      if (old) clearTimeout(old);
      timers.current.delete(toast.id);
      setToasts((list) => [...list.filter((t) => t.id !== toast.id), toast]);
      if (!toast.persistent) {
        timers.current.set(
          toast.id,
          setTimeout(() => dismiss(toast.id), TOAST_MS),
        );
      }
    },
    [dismiss],
  );

  const setDock = useCallback((owner: symbol, node: ReactNode | null) => {
    setDockState((current) => {
      if (node !== null) return { owner, node };
      return current?.owner === owner ? null : current;
    });
  }, []);

  useEffect(() => {
    const all = timers.current;
    return () => all.forEach((timer) => clearTimeout(timer));
  }, []);

  const value = useMemo(
    () => ({ toasts, dock: dock?.node ?? null, setDock, show, dismiss }),
    [toasts, dock, setDock, show, dismiss],
  );
  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

/** Show and dismiss toasts. A no-op outside a provider, so components work in plain tests. */
export function useToast(): ToastApi {
  const state = useContext(ToastContext);
  // Stable while the provider lives: `show` and `dismiss` never change, the toast list does.
  const show = state?.show;
  const dismiss = state?.dismiss;
  return useMemo(() => (show && dismiss ? { show, dismiss } : NO_OP), [show, dismiss]);
}

/** Keep `node` docked above the tab bar while the caller is mounted; null removes it. */
export function useToastDock(node: ReactNode | null) {
  const setDock = useContext(ToastContext)?.setDock;
  const [owner] = useState(() => Symbol("toast-dock"));
  useEffect(() => {
    setDock?.(owner, node);
  }, [setDock, owner, node]);
  useEffect(() => () => setDock?.(owner, null), [setDock, owner]);
}

export function useToastState() {
  return useContext(ToastContext);
}
