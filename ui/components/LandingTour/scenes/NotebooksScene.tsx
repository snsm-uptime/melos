import { NotebookIcon, RecipeIcon } from "@/app/icons";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { inAt, MiniCard, popAt, Scene, Swap } from "./parts";

/** Notebooks (FR-006.2): a notebook's recipes, one opened, servings scaled from 4 to 2. */
export function NotebooksScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.notebooks;
  const [opened] = t.recipes;
  return (
    <Scene>
      <MiniCard title={t.notebook} icon={<NotebookIcon />}>
        <div className="grid grid-cols-3 gap-2">
          {t.recipes.map((recipe, index) => (
            <span
              key={recipe}
              className={`flex min-w-0 flex-col items-center gap-1 rounded-[var(--radius-sm)] border px-1 py-2 text-center text-[0.7rem] [&_svg]:size-5 ${
                index === 0 ? `border-accent text-accent ${popAt(1)}` : "border-border text-muted"
              }`}
            >
              <RecipeIcon />
              <span className="line-clamp-2 w-full">{recipe}</span>
            </span>
          ))}
        </div>
      </MiniCard>

      <MiniCard title={opened} icon={<RecipeIcon />} className={inAt(2)}>
        <div className="flex items-center gap-2">
          <span className="text-muted">{t.servings}</span>
          <span className="rounded-[var(--radius-sm)] border border-accent px-2 font-semibold text-accent">
            <Swap before="4" after="2" slot={3} />
          </span>
        </div>
        <ul className="m-0 flex list-none flex-col gap-1 p-0">
          {t.lines.map((line) => (
            <li key={line.name} className="flex min-w-0 justify-between gap-2">
              <span className="min-w-0 truncate">{line.name}</span>
              <span className="shrink-0 font-semibold">
                <Swap before={line.before} after={line.after} slot={4} />
              </span>
            </li>
          ))}
        </ul>
      </MiniCard>
    </Scene>
  );
}
