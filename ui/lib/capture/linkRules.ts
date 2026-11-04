/**
 * Link rules for the link capture field (spec 026). They mirror `api/domain/page_link.py` only
 * to enable the submit button and show the field messages; the api is the authority and also
 * refuses ports, credentials and private addresses.
 */

export const MAX_LINK_CHARS = 2048;

export type LinkCheck =
  | { ok: true; url: string }
  | { ok: false; reason: "empty" | "invalid" | "too_long" };

const SCHEME_WITH_SLASHES = /^[A-Za-z][A-Za-z0-9+.-]*:\/\//;
const BARE_SCHEME = /^[A-Za-z][A-Za-z0-9+.-]*:(?!\d)/;

export function checkLink(raw: string): LinkCheck {
  const text = raw.trim();
  if (!text) return { ok: false, reason: "empty" };
  if (text.length > MAX_LINK_CHARS) return { ok: false, reason: "too_long" };
  if (/\s/.test(text)) return { ok: false, reason: "invalid" };

  let candidate = text;
  if (!SCHEME_WITH_SLASHES.test(candidate)) {
    if (BARE_SCHEME.test(candidate)) return { ok: false, reason: "invalid" };
    candidate = `https://${candidate}`;
  }

  let parsed: URL;
  try {
    parsed = new URL(candidate);
  } catch {
    return { ok: false, reason: "invalid" };
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return { ok: false, reason: "invalid" };
  }
  // A host with at least one dot or an IP literal; "example" alone is not a web address.
  const host = parsed.hostname;
  if (!host || (!host.includes(".") && !host.startsWith("["))) {
    return { ok: false, reason: "invalid" };
  }
  if (candidate.length > MAX_LINK_CHARS) return { ok: false, reason: "too_long" };
  return { ok: true, url: candidate };
}
