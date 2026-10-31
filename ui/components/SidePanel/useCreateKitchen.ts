"use client";

import { useState } from "react";

import { createKitchen } from "@/app/kitchens/kitchensClient";
import type { Locale } from "@/lib/i18n/locale";
import { kitchensMessages } from "@/lib/i18n/kitchens";

/** The name, validation and save shared by the inline row and the no-kitchens dialog. */
export function useCreateKitchen(locale: Locale) {
  const t = kitchensMessages[locale];
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  /** True once the kitchen exists. */
  async function submit(): Promise<boolean> {
    if (pending) return false;
    if (name.trim().length === 0) {
      setError(t.errorInvalidName);
      return false;
    }
    setPending(true);
    setError(null);
    const result = await createKitchen(name, t);
    setPending(false);
    if (!result.ok) {
      setError(result.error);
      return false;
    }
    setName("");
    return true;
  }

  return { name, setName, error, pending, submit };
}
