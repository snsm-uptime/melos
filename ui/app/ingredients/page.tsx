import { IngredientsScreen } from "@/components/Ingredients/IngredientsScreen";
import { requireAlias } from "@/lib/alias";
import { getServerLocale } from "@/lib/serverLocale";

export const dynamic = "force-dynamic";

/** Where the person buys each ingredient (spec 070 US2). */
export default async function IngredientsPage() {
  await requireAlias("/ingredients");
  const locale = await getServerLocale();
  return <IngredientsScreen locale={locale} />;
}
