/** Client helpers for kitchen create/rename/open via same-origin BFF. */

import {
  patchMembershipKitchens,
  replaceMembershipKitchens,
} from "./membershipKitchensStore";

export type KitchenMember = {
  user_id: string;
  /** Null only while a member has not passed the alias gate yet. */
  alias: string | null;
  photo_base64?: string | null;
};

/**
 * Person label for rosters and pickers. Email is an identity surface and is
 * never a label, so a member still missing an alias falls back to a short id.
 */
export function memberLabel(member: KitchenMember): string {
  return member.alias ?? `${member.user_id.slice(0, 8)}…`;
}

export type KitchenItem = {
  id: string;
  name: string;
  owner_id: string;
  role: string;
  members?: KitchenMember[];
  /** Archive state (Story 9.1's API always includes this field). */
  is_archived?: boolean;
};

export type KitchensClientMessages = {
  errorGeneric: string;
  errorInvalidName: string;
  errorForbidden: string;
  errorUnauthorized: string;
  errorInvalidEmail?: string;
  errorAlreadyMember?: string;
  errorSmtp?: string;
};

type ErrorResult = { ok: false; error: string };
type OkCreate = { ok: true; kitchen: { id: string; name: string; owner_id: string } };
type OkRename = {
  ok: true;
  kitchen: { id: string; name: string; owner_id: string; is_archived?: boolean };
};
type OkSimple = { ok: true };

type KitchenPayload = {
  id?: string;
  name?: string;
  owner_id?: string;
  is_archived?: boolean;
};

function mapError(
  status: number,
  body: { detail?: unknown; code?: unknown } | null,
  messages: KitchensClientMessages,
): string {
  const code = typeof body?.code === "string" ? body.code : "";
  if (status === 401) return messages.errorUnauthorized;
  if (status === 403) return messages.errorForbidden;
  if (status === 409 || code === "already_kitchen_member") {
    return messages.errorAlreadyMember ?? messages.errorGeneric;
  }
  if (status === 422 || code === "invalid_kitchen_name" || code === "invalid_invite_email") {
    return messages.errorInvalidEmail ?? messages.errorInvalidName;
  }
  if (status === 503 || code === "smtp_send_error" || code === "smtp_config_error") {
    return messages.errorSmtp ?? messages.errorGeneric;
  }
  return messages.errorGeneric;
}

async function parseJson(response: Response): Promise<unknown | null> {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function asKitchenPayload(data: unknown): KitchenPayload | null {
  if (!data || typeof data !== "object") return null;
  return data as KitchenPayload;
}

type OkKitchens = { ok: true; kitchens: KitchenItem[] };

export async function fetchKitchens(
  messages: KitchensClientMessages,
  options: { archived?: boolean } = {},
): Promise<OkKitchens | ErrorResult> {
  const url = options.archived ? "/api/kitchens?archived=true" : "/api/kitchens";
  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
  } catch {
    return { ok: false, error: messages.errorGeneric };
  }
  if (!response.ok) {
    const body = (await parseJson(response)) as { detail?: unknown; code?: unknown } | null;
    return { ok: false, error: mapError(response.status, body, messages) };
  }
  const data = (await parseJson(response)) as { kitchens?: unknown } | null;
  if (!data || !Array.isArray(data.kitchens)) {
    return { ok: false, error: messages.errorGeneric };
  }
  const kitchens = data.kitchens as KitchenItem[];
  // Only the non-archived fetch feeds the shared membership store — source-kitchen
  // pickers elsewhere (Budgets, InviteForm) must never see archived-only data.
  if (!options.archived) replaceMembershipKitchens(kitchens);
  return { ok: true, kitchens };
}

export async function createKitchen(
  name: string,
  messages: KitchensClientMessages,
): Promise<OkCreate | ErrorResult> {
  let response: Response;
  try {
    response = await fetch("/api/kitchens", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ name }),
    });
  } catch {
    return { ok: false, error: messages.errorGeneric };
  }
  if (!response.ok) {
    const body = (await parseJson(response)) as {
      detail?: unknown;
      code?: unknown;
    } | null;
    return { ok: false, error: mapError(response.status, body, messages) };
  }
  const data = asKitchenPayload(await parseJson(response));
  if (!data?.id || !data.name || !data.owner_id) {
    return { ok: false, error: messages.errorGeneric };
  }
  const kitchen = { id: data.id, name: data.name, owner_id: data.owner_id };
  patchMembershipKitchens((prev) => {
    if (prev.some((item) => item.id === kitchen.id)) return prev;
    return [
      ...prev,
      {
        id: kitchen.id,
        name: kitchen.name,
        owner_id: kitchen.owner_id,
        role: "owner",
        balance_crc: "0",
        total_crc: "0",
      },
    ];
  });
  return { ok: true, kitchen };
}

export async function renameKitchen(
  kitchenId: string,
  name: string,
  messages: KitchensClientMessages,
): Promise<OkRename | ErrorResult> {
  let response: Response;
  try {
    response = await fetch(`/api/kitchens/${encodeURIComponent(kitchenId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ name }),
    });
  } catch {
    return { ok: false, error: messages.errorGeneric };
  }
  if (!response.ok) {
    const body = (await parseJson(response)) as {
      detail?: unknown;
      code?: unknown;
    } | null;
    return { ok: false, error: mapError(response.status, body, messages) };
  }
  const data = asKitchenPayload(await parseJson(response));
  if (!data?.id || !data.name || !data.owner_id) {
    return { ok: false, error: messages.errorGeneric };
  }
  const kitchen = { id: data.id, name: data.name, owner_id: data.owner_id };
  patchMembershipKitchens((prev) =>
    prev.map((item) => (item.id === kitchen.id ? { ...item, name: kitchen.name } : item)),
  );
  return { ok: true, kitchen };
}

export async function deleteKitchen(
  kitchenId: string,
  messages: KitchensClientMessages,
): Promise<OkSimple | ErrorResult> {
  let response: Response;
  try {
    response = await fetch(`/api/kitchens/${encodeURIComponent(kitchenId)}`, {
      method: "DELETE",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
  } catch {
    return { ok: false, error: messages.errorGeneric };
  }
  if (!response.ok) {
    const body = (await parseJson(response)) as {
      detail?: unknown;
      code?: unknown;
    } | null;
    return { ok: false, error: mapError(response.status, body, messages) };
  }
  patchMembershipKitchens((prev) => prev.filter((item) => item.id !== kitchenId));
  return { ok: true };
}

async function postKitchenAction(
  kitchenId: string,
  action: "archive" | "unarchive",
  messages: KitchensClientMessages,
): Promise<OkRename | ErrorResult> {
  let response: Response;
  try {
    response = await fetch(`/api/kitchens/${encodeURIComponent(kitchenId)}/${action}`, {
      method: "POST",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
  } catch {
    return { ok: false, error: messages.errorGeneric };
  }
  if (!response.ok) {
    const body = (await parseJson(response)) as {
      detail?: unknown;
      code?: unknown;
    } | null;
    return { ok: false, error: mapError(response.status, body, messages) };
  }
  const data = asKitchenPayload(await parseJson(response));
  if (!data?.id || !data.name || !data.owner_id) {
    return { ok: false, error: messages.errorGeneric };
  }
  return {
    ok: true,
    kitchen: { id: data.id, name: data.name, owner_id: data.owner_id, is_archived: data.is_archived },
  };
}

/**
 * Archives a kitchen the caller owns (Story 9.1's `POST /kitchens/{id}/archive`).
 * Removes it from the shared non-archived membership store immediately —
 * same removal shape `deleteKitchen` already uses.
 */
export async function archiveKitchen(
  kitchenId: string,
  messages: KitchensClientMessages,
): Promise<OkRename | ErrorResult> {
  const result = await postKitchenAction(kitchenId, "archive", messages);
  if (result.ok) {
    patchMembershipKitchens((prev) => prev.filter((item) => item.id !== kitchenId));
  }
  return result;
}

/** Unarchives a kitchen the caller owns (Story 9.1's `POST /kitchens/{id}/unarchive`). */
export async function unarchiveKitchen(
  kitchenId: string,
  messages: KitchensClientMessages,
): Promise<OkRename | ErrorResult> {
  const result = await postKitchenAction(kitchenId, "unarchive", messages);
  if (result.ok) {
    const { id, name, owner_id } = result.kitchen;
    patchMembershipKitchens((prev) =>
      prev.some((item) => item.id === id)
        ? prev
        : [...prev, { id, name, owner_id, role: "owner", is_archived: false }],
    );
  }
  return result;
}

/** Persist last-opened via /auth/me (account column) after ACL on the API. */
export async function setLastOpenedKitchen(
  kitchenId: string,
  messages: KitchensClientMessages,
): Promise<OkSimple | ErrorResult> {
  let response: Response;
  try {
    response = await fetch("/api/auth/me", {
      method: "PATCH",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ last_opened_kitchen_id: kitchenId }),
    });
  } catch {
    return { ok: false, error: messages.errorGeneric };
  }
  if (!response.ok) {
    const body = (await parseJson(response)) as {
      detail?: unknown;
      code?: unknown;
    } | null;
    return { ok: false, error: mapError(response.status, body, messages) };
  }
  return { ok: true };
}

export type InviteSent = {
  status: string;
  template_kind: string;
  invite_id: string;
};

type OkInvite = { ok: true; invite: InviteSent };

export async function inviteMember(
  kitchenId: string,
  email: string,
  messages: KitchensClientMessages,
): Promise<OkInvite | ErrorResult> {
  let response: Response;
  try {
    response = await fetch(`/api/kitchens/${encodeURIComponent(kitchenId)}/invites`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ email }),
    });
  } catch {
    return { ok: false, error: messages.errorGeneric };
  }
  if (!response.ok) {
    const body = (await parseJson(response)) as {
      detail?: unknown;
      code?: unknown;
    } | null;
    return { ok: false, error: mapError(response.status, body, messages) };
  }
  const data = (await parseJson(response)) as {
    status?: string;
    template_kind?: string;
    invite_id?: string;
  } | null;
  if (!data?.status || data.status !== "sent" || !data.invite_id || !data.template_kind) {
    return { ok: false, error: messages.errorGeneric };
  }
  return {
    ok: true,
    invite: {
      status: data.status,
      template_kind: data.template_kind,
      invite_id: data.invite_id,
    },
  };
}

type OkMembers = { ok: true; members: KitchenMember[] };

export async function fetchKitchenMembers(
  kitchenId: string,
  messages: KitchensClientMessages,
): Promise<OkMembers | ErrorResult> {
  let response: Response;
  try {
    response = await fetch(`/api/kitchens/${encodeURIComponent(kitchenId)}/members`, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    });
  } catch {
    return { ok: false, error: messages.errorGeneric };
  }
  if (!response.ok) {
    const body = (await parseJson(response)) as {
      detail?: unknown;
      code?: unknown;
    } | null;
    return { ok: false, error: mapError(response.status, body, messages) };
  }
  const data = (await parseJson(response)) as { members?: unknown } | null;
  if (!data || !Array.isArray(data.members)) {
    return { ok: false, error: messages.errorGeneric };
  }
  const members: KitchenMember[] = [];
  for (const row of data.members) {
    if (!row || typeof row !== "object") {
      return { ok: false, error: messages.errorGeneric };
    }
    const m = row as { user_id?: unknown; alias?: unknown; photo_base64?: unknown };
    if (typeof m.user_id !== "string") {
      return { ok: false, error: messages.errorGeneric };
    }
    members.push({
      user_id: m.user_id,
      alias: typeof m.alias === "string" && m.alias ? m.alias : null,
      photo_base64: typeof m.photo_base64 === "string" ? m.photo_base64 : null,
    });
  }
  return { ok: true, members };
}
