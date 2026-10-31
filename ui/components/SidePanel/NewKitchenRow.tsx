"use client";

import { useEffect, useRef, type FormEvent } from "react";

import { SaveIcon } from "@/app/icons";
import { IconButton } from "@/components/IconButton";
import type { Locale } from "@/lib/i18n/locale";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import { sidePanelMessages } from "@/lib/i18n/sidePanel";
import { KitchenIcon } from "./KitchenIcon";
import { useCreateKitchen } from "./useCreateKitchen";

/** The panel's "+": a kitchen row with a name input and save. Escape or a click outside cancels. */
export function NewKitchenRow({
  locale,
  onCancel,
  onCreated,
}: {
  locale: Locale;
  onCancel: () => void;
  onCreated: () => void;
}) {
  const t = kitchensMessages[locale];
  const { name, setName, error, pending, submit } = useCreateKitchen(locale);
  const rowRef = useRef<HTMLLIElement>(null);

  useEffect(() => {
    if (pending) return;
    function onPointerDown(event: PointerEvent) {
      const target = event.target as Element;
      // The "+" closes the row itself; cancelling here would make its click reopen it.
      if (
        rowRef.current?.contains(target) ||
        target.closest("[data-new-kitchen-toggle]")
      )
        return;
      onCancel();
    }
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [pending, onCancel]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (await submit()) onCreated();
  }

  return (
    <li ref={rowRef} className="min-w-0">
      <form
        className="flex min-h-11 min-w-0 items-center gap-1"
        onSubmit={(event) => void onSubmit(event)}
      >
        <span className="ml-2 mr-2 flex shrink-0">
          <KitchenIcon id="new-kitchen" name={name} />
        </span>
        <input
          autoFocus
          type="text"
          aria-label={t.createLabel}
          placeholder={t.createLabel}
          value={name}
          maxLength={200}
          autoComplete="off"
          disabled={pending}
          className="min-w-0 flex-1 border-0 border-b border-border bg-transparent py-1 text-[0.9rem] text-foreground outline-none focus:border-accent"
          onChange={(event) => setName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== "Escape") return;
            event.stopPropagation();
            onCancel();
          }}
        />
        <IconButton
          type="submit"
          variant="ghost"
          className="size-11"
          label={sidePanelMessages[locale].renameSave}
          disabled={pending}
          icon={<SaveIcon className="size-5" />}
        />
      </form>
      {error ? (
        <p className="m-0 px-2 text-[0.8rem] text-owe" role="alert">
          {error}
        </p>
      ) : null}
    </li>
  );
}
