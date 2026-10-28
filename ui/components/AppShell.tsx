// Reused from finance-dashboard/ui/components/AppShell.tsx
"use client";

import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { BackIcon, HomeIcon, NotebookIcon } from "@/app/icons";
import {
  ChromeBackProvider,
  chromeHeaderIsActive,
  useChromeHeaderState,
} from "@/components/ChromeBack";
import { IconButton } from "@/components/IconButton";
import { usePreferences } from "@/components/PreferencesProvider";
import { TabBar, type TabBarItem } from "@/components/soft-ledger/TabBar";
import { showsAppChrome, showsFloatingLanguageSwitch, tabKeyFromPath } from "@/lib/appChrome";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { Chip } from "./Chip";
import { SignedOutLanguageSwitch } from "./SignedOutLanguageSwitch";

/** Persistent application chrome around authenticated pages. Auth/setup routes skip it. */
export function AppShell({ children }: { children: ReactNode }) {
  return (
    <ChromeBackProvider>
      <AppShellFrame>{children}</AppShellFrame>
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
  // gaining the authenticated TabBar that showsAppChrome gates.
  const showTabBar = showsAppChrome(pathname);

  // Recipes, cart and chat tabs join Home as those features land.
  const tabs: TabBarItem[] = [
    { key: "home", href: "/home", label: t.tabHome, Icon: HomeIcon },
    { key: "notebook", href: "/notebooks", label: t.tabNotebook, Icon: NotebookIcon },
  ];

  // The English/Spanish switch of the signed-out screens (spec 063 FR-017), on both layouts:
  // /sign-in opts into the header, the other signed-out screens have none. /sign-in puts its
  // switch in its own card, below the sign-up link, so none floats there.
  const languageSwitch = showsFloatingLanguageSwitch(pathname) ? <SignedOutLanguageSwitch /> : null;

  if (!showHeader && !showTabBar) {
    return (
      <div className="fixed inset-0 overflow-y-auto">
        {languageSwitch}
        {children}
      </div>
    );
  }

  return (
    <div className="fixed inset-0 flex flex-col overflow-hidden">
      <div className="relative flex flex-col flex-1 min-h-0">
        {languageSwitch}
        {header.progressBar ? <div className="shrink-0">{header.progressBar}</div> : null}
        {showHeader ? (
          <header
            data-app-chrome="header"
            className={`flex shrink-0 items-center gap-2 ${
              header.progressBar
                ? "pt-[max(1rem,env(safe-area-inset-top))]"
                : "pt-[max(0.5rem,env(safe-area-inset-top))]"
            } pr-[max(1rem,env(safe-area-inset-right))] pb-1 pl-[max(0.5rem,env(safe-area-inset-left))]`}
          >
            <div className="flex w-10 shrink-0 items-center justify-start self-center">
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
      </div>
      {showTabBar ? (
        <TabBar items={tabs} ariaLabel={t.tabNavAria} active={tabKeyFromPath(pathname)} />
      ) : null}
    </div>
  );
}
