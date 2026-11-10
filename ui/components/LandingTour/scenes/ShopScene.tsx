"use client";

import { CartEntryRow } from "@/components/Cart/CartEntryRow";
import { ShoppingLineRow } from "@/components/ShoppingList/ShoppingLine";
import { TabButton, TabList } from "@/components/Tabs";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";

import { cartEntries, shoppingLines } from "./data";
import { ignore, inAt, Rows, Scene, Swap, type Slot } from "./parts";

/**
 * Plan and shop (FR-006.4): the cart's two recipes, then the shopping list with flour from both on
 * one line, 1 cup + 3 tbsp, with both recipes' chips; on the Market tab, eggs and milk are checked
 * as bought. The cart rows, tabs and list rows are the app's. The tabs are TabList without the
 * arrows of PlaceTabs, whose scroll-into-view would move the landing page.
 */
export function ShopScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.shop;
  const l = shoppingListMessages[locale];
  const lines = shoppingLines(locale);
  const [entryA, entryB] = cartEntries(locale);
  // Each state of the tabs is drawn once, so its ids carry the state.
  const tabs = (market: boolean, left: number) => {
    const id = `demo-shop-${market ? "market" : "all"}-${left}`;
    return (
      <TabList label={l.placeTabs}>
        <TabButton id={`${id}-all`} selected={!market} onSelect={ignore} icon={null} label={l.allPlaces} />
        <TabButton id={`${id}-market`} selected={market} onSelect={ignore} icon={null} label={l.tabCount(t.placeMarket, left)} />
        <TabButton id={`${id}-bakery`} selected={false} onSelect={ignore} icon={null} label={l.tabCount(t.placeBakery, 1)} />
      </TabList>
    );
  };
  const bought: { key: string; slot: Slot; line: typeof lines.eggs }[] = [
    { key: "eggs", slot: 5, line: lines.eggs },
    { key: "milk", slot: 6, line: lines.milk },
  ];
  return (
    <Scene>
      <div className="flex flex-col gap-2">
        <Rows className={inAt(1)}>
          <CartEntryRow entry={entryA} factor={entryA.factor} locale={locale} />
        </Rows>
        <Rows className={inAt(2)}>
          <CartEntryRow entry={entryB} factor={entryB.factor} locale={locale} />
        </Rows>
      </div>
      <div className={`flex flex-col gap-2 ${inAt(3)}`}>
        <Swap
          slot={4}
          before={tabs(false, 3)}
          after={
            <Swap
              slot={5}
              before={tabs(true, 3)}
              after={<Swap slot={6} before={tabs(true, 2)} after={tabs(true, 1)} />}
            />
          }
        />
        <Rows>
          <ShoppingLineRow line={lines.flour} locale={locale} onToggle={ignore} />
        </Rows>
        {bought.map(({ key, slot, line }) => (
          <Swap
            key={key}
            slot={slot}
            before={
              <Rows>
                <ShoppingLineRow line={{ ...line, bought: false }} locale={locale} onToggle={ignore} />
              </Rows>
            }
            after={
              <Rows>
                <ShoppingLineRow line={{ ...line, bought: true }} locale={locale} onToggle={ignore} />
              </Rows>
            }
          />
        ))}
      </div>
    </Scene>
  );
}
