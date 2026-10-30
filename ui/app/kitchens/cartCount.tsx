"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

type CartCount = { count: number | null; setCount: (count: number | null) => void };

const CartCountContext = createContext<CartCount | null>(null);

/**
 * Carries the number of recipes in the kitchen's cart from the notebooks section, which loads
 * the cart, to the header's cart button on the same page. Null until the cart is known.
 */
export function KitchenCartCountProvider({ children }: { children: ReactNode }) {
  const [count, setCount] = useState<number | null>(null);
  const value = useMemo(() => ({ count, setCount }), [count]);
  return <CartCountContext.Provider value={value}>{children}</CartCountContext.Provider>;
}

/** The recipes in the cart as I see them, or null when unknown or there is no provider. */
export function useKitchenCartCount(): number | null {
  return useContext(CartCountContext)?.count ?? null;
}

/** Tell the header how many recipes are in the cart; a no-op without a provider. */
export function usePublishKitchenCartCount(count: number | null): void {
  const setCount = useContext(CartCountContext)?.setCount;
  useEffect(() => {
    setCount?.(count);
  }, [setCount, count]);
}
