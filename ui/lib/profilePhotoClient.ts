/** Saves or clears the signed-in person's photo via the same-origin BFF. */
export async function saveProfilePhoto(photoBase64: string | null): Promise<boolean> {
  try {
    const response = await fetch("/api/auth/me", {
      method: "PATCH",
      credentials: "same-origin",
      cache: "no-store",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify({ photo_base64: photoBase64 }),
    });
    return response.ok;
  } catch {
    return false;
  }
}
