"use client";

import { useSyncExternalStore } from "react";

import type { KitchenItem } from "./kitchensClient";

let snapshot: KitchenItem[] | null = null;
const listeners = new Set<() => void>();

function emit() {
  for (const listener of listeners) listener();
}

export function subscribeMembershipKitchens(onChange: () => void): () => void {
  listeners.add(onChange);
  return () => {
    listeners.delete(onChange);
  };
}

export function getMembershipKitchensSnapshot(): KitchenItem[] | null {
  return snapshot;
}

/** Replace the in-memory membership roster (GET /kitchens or first paint). */
export function replaceMembershipKitchens(next: KitchenItem[]): void {
  snapshot = next;
  emit();
}

export function patchMembershipKitchens(update: (prev: KitchenItem[]) => KitchenItem[]): void {
  snapshot = update(snapshot ?? []);
  emit();
}

export function resetMembershipKitchensStore(): void {
  snapshot = null;
  emit();
}

export function useMembershipKitchens(): KitchenItem[] | null {
  return useSyncExternalStore(
    subscribeMembershipKitchens,
    getMembershipKitchensSnapshot,
    () => null,
  );
}
