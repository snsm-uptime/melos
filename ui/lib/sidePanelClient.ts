/** Client helpers for the side panel via the same-origin BFF (spec 064, contracts/side-panel-api.md). */

export type SidePanelData = {
  default_kitchen_id: string | null;
  recipes_added: number;
  notebooks: number;
};

const listeners = new Set<() => void>();

/** Called by the panel, to reload after a kitchen action outside it. */
export function subscribeSidePanelRefresh(onRefresh: () => void): () => void {
  listeners.add(onRefresh);
  return () => {
    listeners.delete(onRefresh);
  };
}

export function requestSidePanelRefresh(): void {
  for (const listener of listeners) listener();
}

async function parse(response: Response): Promise<SidePanelData | null> {
  if (!response.ok) return null;
  try {
    const data = (await response.json()) as Partial<SidePanelData> | null;
    if (typeof data?.recipes_added !== "number" || typeof data.notebooks !== "number") return null;
    return {
      default_kitchen_id: data.default_kitchen_id ?? null,
      recipes_added: data.recipes_added,
      notebooks: data.notebooks,
    };
  } catch {
    return null;
  }
}

export async function fetchSidePanel(): Promise<SidePanelData | null> {
  try {
    return await parse(
      await fetch("/api/side-panel", {
        method: "GET",
        headers: { Accept: "application/json" },
        credentials: "same-origin",
        cache: "no-store",
      }),
    );
  } catch {
    return null;
  }
}

export async function setDefaultKitchen(kitchenId: string): Promise<SidePanelData | null> {
  try {
    return await parse(
      await fetch("/api/side-panel/default-kitchen", {
        method: "PUT",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ kitchen_id: kitchenId }),
      }),
    );
  } catch {
    return null;
  }
}
