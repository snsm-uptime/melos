// Reused from finance-dashboard/ui/components/AppShell.tsx
"use client";

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useState, type ReactNode } from "react";

import { BackIcon, MenuIcon } from "@/app/icons";
import {
  ChromeBackProvider,
  chromeHeaderIsActive,
  useChromeHeaderState,
} from "@/components/ChromeBack";
import { IconButton } from "@/components/IconButton";
import { usePreferences } from "@/components/PreferencesProvider";
import { SidePanel } from "@/components/SidePanel";
import { ToastProvider, ToastViewport } from "@/components/Toast";
import { showsAppChrome, showsFloatingLanguageSwitch } from "@/lib/appChrome";
import { cartMessages } from "@/lib/i18n/cart";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { sidePanelMessages } from "@/lib/i18n/sidePanel";
import { Chip } from "./Chip";
import { SignedOutLanguageSwitch } from "./SignedOutLanguageSwitch";

/** Persistent application chrome around authenticated pages. Auth/setup routes skip it. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <ChromeBackProvider>
      <ToastProvider>
        <AppShellFrame>{children}</AppShellFrame>
      </ToastProvider>
    </ChromeBackProvider>
  );
}

function AppShellFrame({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "";
  const router = useRouter();
  const { locale } = usePreferences();
  const t = kitchensMessages[locale];
  const header = useChromeHeaderState();
  const showHeader = chromeHeaderIsActive(header);
  // Decoupled from showHeader: public screens (e.g. /sign-in) opt into
  // just the header — a way back to "/" — via useChromeHeader, without also
  // gaining the authenticated side panel that showsAppChrome gates.
  const showPanel = showsAppChrome(pathname);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  // The header sits on the page gutter so it lines up with the content below it. Icon buttons at
  // its start keep the tighter inset: Back, and on phones the panel's menu button.
  const headerInset =
    header.onBack || header.backHref
      ? "pl-[max(0.5rem,env(safe-area-inset-left))]"
      : header.leading || !showPanel
        ? "pl-[max(var(--page-gutter),env(safe-area-inset-left))]"
        : "pl-[max(0.5rem,env(safe-area-inset-left))] md:pl-[max(var(--page-gutter),env(safe-area-inset-left))]";

  // The English/Spanish switch of the signed-out screens (spec 063 FR-017), on both layouts:
  // /sign-in opts into the header, the other signed-out screens have none. /sign-in puts its
  // switch in its own card, below the sign-up link, so none floats there.
  const languageSwitch = showsFloatingLanguageSwitch(pathname) ? <SignedOutLanguageSwitch /> : null;
  const dismissLabel = cartMessages[locale].dismiss;

  if (!showHeader && !showPanel) {
    return (
      <div className="fixed inset-0 overflow-y-auto">
        {languageSwitch}
        {children}
        <ToastViewport
          dismissLabel={dismissLabel}
          className="fixed inset-x-0 bottom-0 z-20 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
        />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 flex overflow-hidden">
      {showPanel ? <SidePanel drawerOpen={drawerOpen} onDrawerClose={closeDrawer} /> : null}
      <div className="relative flex min-w-0 flex-col flex-1 min-h-0">
        {languageSwitch}
        {header.progressBar ? <div className="shrink-0">{header.progressBar}</div> : null}
        {showHeader || showPanel ? (
          <header
            data-app-chrome="header"
            className={`flex shrink-0 items-center gap-2 ${showHeader ? "" : "md:hidden "}${
              header.progressBar
                ? "pt-[max(1rem,env(safe-area-inset-top))]"
                : "pt-[max(0.5rem,env(safe-area-inset-top))]"
            } pr-[max(var(--page-gutter),env(safe-area-inset-right))] pb-1 ${headerInset}`}
          >
            {showPanel ? (
              <span className="inline-flex shrink-0 md:hidden">
                <IconButton
                  variant="ghost"
                  className="size-11"
                  label={sidePanelMessages[locale].open}
                  aria-haspopup="dialog"
                  icon={<MenuIcon className="size-6" />}
                  onClick={() => setDrawerOpen(true)}
                />
              </span>
            ) : null}
            <div className="flex w-10 shrink-0 items-center justify-start self-center empty:hidden">
              {header.onBack || header.backHref ? (
                <IconButton
                  variant="ghost"
                  label={t.chromeBack}
                  icon={<BackIcon className="size-6" />}
                  onClick={() => {
                    if (header.onBack) {
                      header.onBack();
                      return;
                    }
                    if (header.backHref) router.push(header.backHref);
                  }}
                />
              ) : header.leading ? (
                header.leading
              ) : null}
            </div>
            <div className="flex min-w-0 flex-1 items-center justify-start gap-2 self-center">
              {header.title ? (
                <h1 className="m-0 min-w-0 truncate text-[1.5rem] font-[550] leading-normal text-foreground">
                  {header.title}
                </h1>
              ) : null}
              {header.details ? (
                <Chip className={header.detailsClassName}>
                  <span className="shrink-0 text-[0.85rem] text-muted">{header.details}</span>
                </Chip>
              ) : null}
            </div>
            {header.trailing ? (
              <div className="flex shrink-0 items-center gap-1 self-center">{header.trailing}</div>
            ) : null}
          </header>
        ) : null}
        <div className="flex min-h-0 flex-1 flex-col overflow-x-hidden overflow-y-auto">{children}</div>
        {/* Toasts sit at the bottom of the content area (spec 064 R12). */}
        <ToastViewport
          dismissLabel={dismissLabel}
          className="absolute inset-x-0 bottom-0 z-20 pb-[max(0.5rem,env(safe-area-inset-bottom))]"
        />
      </div>
    </div>
  );
}
