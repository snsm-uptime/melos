import { IngredientsScreen } from "@/components/Ingredients/IngredientsScreen";
import { requireAlias } from "@/lib/alias";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

/** Where the person buys each ingredient (spec 070 US2). */
export default async function IngredientsPage() {
  await requireAlias("/ingredients");
  const locale = await getServerLocale();
  return (
    <main className="flex min-w-0 flex-1 flex-col px-page-gutter pt-2 pb-6">
      <IngredientsScreen locale={locale} />
    </main>
  );
}
