"use client";

import { useState } from "react";

import { MoonIcon, SettingsIcon, SunIcon, SystemIcon } from "@/app/icons";
import { LanguageChoice } from "@/components/LanguageChoice";
import { usePreferences } from "@/components/PreferencesProvider";
import { SlideDown } from "@/components/SlideDown";
import { TriSwitch } from "@/components/TriSwitch";
import { accountCopy } from "@/lib/i18n/account";
import type { ThemePreference } from "@/lib/i18n/locale";
import { sidePanelMessages } from "@/lib/i18n/sidePanel";
import { signOut } from "@/lib/signOut";
import { panelEntryClass, usePanelLayout } from "./panelLayout";
import { SidePanelEntry } from "./SidePanelEntry";

const headingClass = "m-0 text-[0.7rem] font-semibold uppercase tracking-[0.04rem] text-muted";

/** Settings above Log out. The footer grows upward, so opening it lifts this entry. */
export function SidePanelSettings({
  expanded,
  onToggle,
}: {
  expanded: boolean;
  onToggle: () => void;
}) {
  const { openOnlyClass } = usePanelLayout();
  const { theme, setTheme, ready, locale } = usePreferences();
  const t = accountCopy(locale);
  const label = sidePanelMessages[locale].settings;
  const [pending, setPending] = useState(false);
  const [signingOut, setSigningOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onTheme(next: ThemePreference) {
    setPending(true);
    setError(null);
    try {
      await setTheme(next);
    } catch {
      setError(t.saveThemeFailed);
    } finally {
      setPending(false);
    }
  }

  function onPasswordReset() {
    setSigningOut(true);
    void signOut("/forgot-password");
  }

  return (
    <>
      <SidePanelEntry
        id="side-panel-settings"
        label={label}
        icon={<SettingsIcon className="size-7 shrink-0 p-0.5" />}
        expanded={expanded}
        controls="side-panel-settings-options"
        onClick={onToggle}
      />
      <div className={openOnlyClass}>
        <SlideDown open={expanded} id="side-panel-settings-options" labelledBy="side-panel-settings">
          <div className="mb-2 flex max-h-[50dvh] flex-col gap-3 overflow-y-auto border-b border-border px-2 pt-2 pb-3">
            <button type="button" className={`${panelEntryClass} !px-0`} disabled={signingOut} onClick={onPasswordReset}>
              {t.passwordReset}
            </button>
            <section className="flex flex-col gap-2">
              <h2 className={headingClass}>{t.theme}</h2>
              <TriSwitch
                aria-label={t.theme}
                value={theme}
                disabled={pending || !ready || signingOut}
                onChange={(next) => void onTheme(next)}
                options={[
                  { value: "light", label: t.light, icon: <SunIcon /> },
                  { value: "system", label: t.system, icon: <SystemIcon /> },
                  { value: "dark", label: t.dark, icon: <MoonIcon /> },
                ]}
              />
              {error ? <p className="m-0 text-[0.8rem] text-owe">{error}</p> : null}
            </section>
            <section className="flex flex-col gap-2">
              <h2 className={headingClass}>{t.language}</h2>
              <LanguageChoice />
            </section>
          </div>
        </SlideDown>
      </div>
    </>
  );
}
