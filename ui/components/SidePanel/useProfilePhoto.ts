"use client";

import { useState, type ChangeEvent } from "react";

import { usePreferences } from "@/components/PreferencesProvider";
import { saveProfilePhoto } from "@/lib/profilePhotoClient";

/** The pick, crop and save flow behind the avatar's edit buttons. */
export function useProfilePhoto(failureMessage: string) {
  const { refresh } = usePreferences();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cropFile, setCropFile] = useState<File | null>(null);
  const [cropOpen, setCropOpen] = useState(false);

  async function save(photoBase64: string | null) {
    setPending(true);
    setError(null);
    if (await saveProfilePhoto(photoBase64)) await refresh();
    else setError(failureMessage);
    setPending(false);
  }

  function onPick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(null);
    setCropFile(file);
    setCropOpen(true);
  }

  return {
    pending,
    error,
    cropFile,
    cropOpen,
    save,
    onPick,
    closeCrop: () => setCropOpen(false),
    failCrop: () => setError(failureMessage),
  };
}
