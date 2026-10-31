"use client";

import { createContext, useContext } from "react";

import iconButtonStyles from "@/components/IconButton/IconButton.module.scss";

/** Timing for anything that moves with the panel; pair with a `transition-[...]`. */
export const PANEL_SLIDE =
  "duration-(--panel-slide) ease-in-out motion-reduce:transition-none";

/** Fades in once the slide ends, so only the icons move. */
const PANEL_REVEAL =
  "transition-opacity delay-(--panel-slide) duration-150 starting:opacity-0 motion-reduce:transition-none";

export const panelEntryClass = [
  "flex min-h-11 w-full min-w-0 items-center gap-3 text-left rounded-[8px] border-0 bg-transparent px-2 text-[0.9rem] text-muted no-underline cursor-pointer disabled:opacity-45 disabled:cursor-not-allowed",
  iconButtonStyles.button,
  iconButtonStyles.ghost,
].join(" ");

export type PanelLayout = {
  /** Open on larger screens, or the drawer, which is always wide. */
  wide: boolean;
  /** Text and controls that need the wide panel. Closing hides them at once. */
  openOnlyClass: string;
  labelClass: string;
};

export function panelLayout(isOpen: boolean, drawerOpen: boolean): PanelLayout {
  const openOnlyClass = isOpen ? PANEL_REVEAL : "md:hidden";
  return {
    wide: isOpen || drawerOpen,
    openOnlyClass,
    labelClass: `min-w-0 flex-1 truncate ${openOnlyClass}`,
  };
}

export const PanelLayoutContext = createContext<PanelLayout>(panelLayout(false, false));

export function usePanelLayout(): PanelLayout {
  return useContext(PanelLayoutContext);
}
