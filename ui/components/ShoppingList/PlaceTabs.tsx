import { TabButton, TabList } from "@/components/Tabs";
import type { Locale } from "@/lib/i18n/locale";
import { shoppingListMessages } from "@/lib/i18n/shoppingList";
import { ALL_TAB, type PlaceTab } from "@/lib/shoppingByPlace";

type PlaceTabsProps = {
  tabs: PlaceTab[];
  selected: string;
  onSelect: (key: string) => void;
  locale: Locale;
};

/**
 * The store tabs of a shopping list (spec 070 FR-014, FR-015): All, then one tab per place with
 * items, each with its count of items not yet bought. One row that scrolls at phone width.
 * Nothing is shown while every item is at the same place.
 */
export function PlaceTabs({ tabs, selected, onSelect, locale }: PlaceTabsProps) {
  const t = shoppingListMessages[locale];
  // With every item at one place, "All" and that place show the same items: no tabs.
  if (tabs.length < 2) return null;
  return (
    <TabList
      label={t.placeTabs}
      cycle={{ previousLabel: t.previousPlace, nextLabel: t.nextPlace }}
    >
      <TabButton
        id="place-tab-all"
        selected={selected === ALL_TAB}
        onSelect={() => onSelect(ALL_TAB)}
        icon={null}
        label={t.allPlaces}
      />
      {tabs.map((tab) => (
        <TabButton
          key={tab.key}
          id={`place-tab-${tab.key.replace(/[^a-z0-9-]/gi, "-")}`}
          selected={selected === tab.key}
          onSelect={() => onSelect(tab.key)}
          icon={null}
          label={t.tabCount(tab.label, tab.left)}
        />
      ))}
    </TabList>
  );
}
