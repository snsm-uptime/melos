"use client";

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  ArchiveToggleIcon,
  LogOutIcon,
  MenuIcon,
  NotebookIcon,
  PlusIcon,
} from "@/app/icons";
import { fetchKitchens, type KitchenItem } from "@/app/kitchens/kitchensClient";
import { useMembershipKitchens } from "@/app/kitchens/membershipKitchensStore";
import { IconButton } from "@/components/IconButton";
import { usePreferences } from "@/components/PreferencesProvider";
import { panelEntryFromPath } from "@/lib/appChrome";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { sidePanelMessages } from "@/lib/i18n/sidePanel";
import {
  fetchSidePanel,
  setDefaultKitchen,
  subscribeSidePanelRefresh,
  type SidePanelData,
} from "@/lib/sidePanelClient";
import { signOut } from "@/lib/signOut";
import { KitchenIcon } from "./KitchenIcon";
import { KitchenStar } from "./KitchenStar";
import { NewKitchenRow } from "./NewKitchenRow";
import { PANEL_SLIDE, panelLayout, PanelLayoutContext } from "./panelLayout";
import { SidePanelEntry } from "./SidePanelEntry";
import { SidePanelIdentity } from "./SidePanelIdentity";
import { SidePanelSettings } from "./SidePanelSettings";
import { useSidePanelState } from "./useSidePanelState";

/** The left panel (spec 064). Below `md` it is a drawer over the content; the shell opens it. */
export function SidePanel({
  drawerOpen,
  onDrawerClose,
}: {
  drawerOpen: boolean;
  onDrawerClose: () => void;
}) {
  const pathname = usePathname() ?? "";
  const router = useRouter();
  const { locale } = usePreferences();
  const t = sidePanelMessages[locale];
  const kt = kitchensMessages[locale];
  const { isOpen, setOpen } = useSidePanelState();
  const kitchens = useMembershipKitchens();
  const [panel, setPanel] = useState<SidePanelData | null>(null);
  const [kitchensError, setKitchensError] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);
  const [archived, setArchived] = useState<KitchenItem[]>([]);
  const [creating, setCreating] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const layout = useMemo(() => panelLayout(isOpen, drawerOpen), [isOpen, drawerOpen]);
  const { wide, openOnlyClass } = layout;

  const reload = useCallback(async () => {
    const [kitchensResult, panelResult] = await Promise.all([
      fetchKitchens(kt),
      fetchSidePanel(),
    ]);
    setKitchensError(kitchensResult.ok ? null : kitchensResult.error);
    setPanel(panelResult);
  }, [kt]);

  // Each page change refreshes the list and the count (research R4).
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading from the api
    void reload();
  }, [pathname, reload]);

  const reloadArchived = useCallback(async () => {
    const result = await fetchKitchens(kt, { archived: true });
    setArchived(result.ok ? result.kitchens : []);
    if (!result.ok) setKitchensError(result.error);
  }, [kt]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- loading from the api
    if (showArchived) void reloadArchived();
  }, [showArchived, pathname, reloadArchived]);

  useEffect(
    () =>
      subscribeSidePanelRefresh(() => {
        void reload();
        if (showArchived) void reloadArchived();
      }),
    [reload, reloadArchived, showArchived],
  );

  useEffect(() => {
    if (!drawerOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onDrawerClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen, onDrawerClose]);

  const defaultKitchenId = panel?.default_kitchen_id ?? null;
  const current = panelEntryFromPath(pathname);

  const listed = useMemo(() => {
    if (showArchived) return archived;
    const isDefault = (id: string) => (id === defaultKitchenId ? 0 : 1);
    return [...(kitchens ?? [])].sort(
      (a, b) =>
        isDefault(a.id) - isDefault(b.id) ||
        a.name.localeCompare(b.name, undefined, { sensitivity: "base" }),
    );
  }, [showArchived, archived, kitchens, defaultKitchenId]);

  async function onSetDefault(kitchenId: string) {
    const result = await setDefaultKitchen(kitchenId);
    setKitchensError(result ? null : kt.errorGeneric);
    if (!result) return;
    setPanel(result);
    router.refresh();
  }

  function onToggle() {
    onDrawerClose();
    if (drawerOpen) return;
    // Closed hides the archive toggle, so its view must not stay on.
    if (isOpen) {
      setShowArchived(false);
      setSettingsOpen(false);
      setCreating(false);
    }
    setOpen(!isOpen);
  }

  function onAddKitchen() {
    if (creating) return setCreating(false);
    // The row is an active kitchen, and needs the wide panel.
    setShowArchived(false);
    if (!wide) setOpen(true);
    setCreating(true);
  }

  function onSettingsToggle() {
    // Closed has no room for the options, so the entry widens the panel first.
    if (!wide) setOpen(true);
    setSettingsOpen((prev) => !wide || !prev);
  }

  function onLogOut() {
    setSigningOut(true);
    void signOut("/sign-in");
  }

  const toggleLabel = wide ? t.close : t.open;
  const logOutLabel = signingOut ? t.loggingOut : t.logOut;

  return (
    <PanelLayoutContext.Provider value={layout}>
      {/* The drawer and its backdrop stay mounted so they can slide and fade out as well as in. */}
      <button
        type="button"
        aria-label={t.close}
        data-side-panel="backdrop"
        className={`fixed inset-0 z-30 border-0 bg-black/40 transition-[opacity,visibility] md:hidden ${PANEL_SLIDE} ${drawerOpen ? "" : "invisible opacity-0"}`}
        onClick={onDrawerClose}
      />
      <nav
        aria-label={t.nav}
        data-side-panel="panel"
        data-open={isOpen}
        className={`fixed inset-y-0 left-0 z-40 flex w-(--panel-width-open) flex-col border-r border-border bg-surface pt-[max(0.5rem,env(safe-area-inset-top))] pb-[max(0.5rem,env(safe-area-inset-bottom))] transition-[translate,visibility] md:static md:z-auto md:shrink-0 md:transition-[width] ${PANEL_SLIDE} ${drawerOpen ? "" : "max-md:invisible max-md:-translate-x-full"} ${isOpen ? "md:w-(--panel-width-open)" : "md:w-(--panel-width-closed)"}`}
      >
        <div className="flex shrink-0 flex-col items-start gap-2 px-2">
          <IconButton
            type="button"
            variant="ghost"
            className="size-11"
            label={toggleLabel}
            aria-expanded={wide}
            icon={<MenuIcon className="size-6" />}
            onClick={onToggle}
          />
        </div>

        <div className="mt-2 min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-2">
          <SidePanelIdentity
            recipeCount={panel ? t.recipeCount(panel.recipes_added) : null}
            notebookCount={panel ? t.notebookCount(panel.notebooks) : null}
          />
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            <li className="min-w-0">
              <SidePanelEntry
                href="/notebooks"
                label={t.notebooks}
                icon={<NotebookIcon className="size-7 shrink-0 p-0.5" />}
                current={current === "notebooks"}
                onClick={onDrawerClose}
              />
            </li>
          </ul>
          <div className="relative mt-3 flex min-h-11 items-center">
            <span
              className={`min-w-0 flex-1 truncate pr-[calc(var(--panel-target)*2)] pl-2 text-[0.7rem] font-semibold uppercase tracking-[0.04rem] text-muted ${openOnlyClass}`}
            >
              {t.kitchens}
            </span>
            {/* Anchored so the row text never pushes the plus during the slide. */}
            <span className={`absolute top-0 right-(--panel-target) ${openOnlyClass}`}>
              <IconButton
                type="button"
                variant="ghost"
                className="size-11"
                label={showArchived ? kt.kitchensShowActive : kt.kitchensShowArchived}
                aria-pressed={showArchived}
                icon={<ArchiveToggleIcon active={showArchived} className="size-5" />}
                onClick={() => setShowArchived((prev) => !prev)}
              />
            </span>
            <IconButton
              type="button"
              variant="ghost"
              className="absolute top-0 right-0 size-11"
              label={kt.createSubmit}
              data-new-kitchen-toggle
              icon={<PlusIcon className="size-5" />}
              onClick={onAddKitchen}
            />
          </div>
          {kitchensError ? (
            <p className={`m-0 px-2 text-[0.8rem] text-owe ${openOnlyClass}`} role="alert">
              {kitchensError}
            </p>
          ) : null}
          {showArchived && listed.length === 0 ? (
            <p className={`m-0 px-2 text-[0.8rem] text-muted ${openOnlyClass}`}>
              {kt.kitchensArchivedEmpty}
            </p>
          ) : null}
          <ul className="m-0 flex list-none flex-col gap-1 p-0">
            {listed.map((kitchen) => (
              <li key={kitchen.id} className="relative min-w-0">
                <SidePanelEntry
                  href={`/kitchens/${encodeURIComponent(kitchen.id)}`}
                  label={kitchen.name}
                  icon={<KitchenIcon id={kitchen.id} name={kitchen.name} />}
                  current={current === `kitchen:${kitchen.id}`}
                  reserveTrailing={!showArchived}
                  onClick={onDrawerClose}
                />
                {showArchived ? null : (
                  <KitchenStar
                    isDefault={kitchen.id === defaultKitchenId}
                    defaultLabel={t.defaultKitchen}
                    setLabel={t.setDefault}
                    onSet={() => void onSetDefault(kitchen.id)}
                  />
                )}
              </li>
            ))}
            {creating ? (
              <NewKitchenRow
                locale={locale}
                onCancel={() => setCreating(false)}
                onCreated={() => {
                  setCreating(false);
                  router.refresh();
                  void reload();
                }}
              />
            ) : null}
          </ul>
        </div>

        <div className="mt-2 shrink-0 border-t border-border px-2 pt-2">
          <SidePanelSettings expanded={settingsOpen} onToggle={onSettingsToggle} />
          <SidePanelEntry
            label={logOutLabel}
            icon={<LogOutIcon className="size-7 shrink-0 p-0.5" />}
            disabled={signingOut}
            onClick={onLogOut}
          />
        </div>
      </nav>
    </PanelLayoutContext.Provider>
  );
}
