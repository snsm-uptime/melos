import { createElement, type ComponentType } from "react";

import { landingMessages, type DemoId } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { DemoFrame } from "./DemoFrame";
import { CaptureScene } from "./scenes/CaptureScene";
import { HomeScene } from "./scenes/HomeScene";
import { IngredientsScene } from "./scenes/IngredientsScene";
import { NotebooksScene } from "./scenes/NotebooksScene";
import { OverviewScene } from "./scenes/OverviewScene";
import { ShopScene } from "./scenes/ShopScene";
import { TogetherScene } from "./scenes/TogetherScene";

type SceneComponent = ComponentType<{ locale: Locale }>;

const SCENES: Record<DemoId, SceneComponent> = {
  overview: OverviewScene,
  capture: CaptureScene,
  notebooks: NotebooksScene,
  together: TogetherScene,
  shop: ShopScene,
  ingredients: IngredientsScene,
  home: HomeScene,
};

/** The scene drawn for a demo: the hero's overview, or a group's. */
export function demoFor(id: DemoId): SceneComponent {
  return SCENES[id];
}

/** A demo in its frame, with its title, description and pause labels in the page's language. */
export function TourDemo({ id, locale }: { id: DemoId; locale: Locale }) {
  const t = landingMessages[locale].demo;
  return (
    <DemoFrame
      id={id}
      title={t[id].title}
      description={t[id].description}
      pauseLabel={t.pause}
      playLabel={t.play}
    >
      {createElement(demoFor(id), { locale })}
    </DemoFrame>
  );
}
