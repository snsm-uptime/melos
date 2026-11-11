/*
 * The signed-out landing page feature tour (spec 075).
 *
 * Reused, never rebuilt (research R2, R5):
 * - `Chip`, `chipClassName` (`accent` | `muted` | `warning`) from `@/components/Chip`;
 * - `cardClassName` from `@/components/Card`;
 * - `CauldronMark` from `@/components/CauldronLoader`;
 * - `PrimaryButton`, `GhostButton` from `@/components/soft-ledger`;
 * - the reduced-motion pattern of `CauldronLoader.module.scss`: the still pose is the resting
 *   style, and motion is declared only inside `@media (prefers-reduced-motion: no-preference)`.
 */

export { ClosingCta, type ClosingCtaProps } from "./ClosingCta";
export { DemoFrame, type DemoFrameProps } from "./DemoFrame";
export { demoFor, TourDemo } from "./demos";
export { ComingSoon, type ComingSoonProps } from "./ComingSoon";
export { Glows, type GlowPlace } from "./Glows";
export { GroupSection, type GroupSectionProps } from "./GroupSection";
export { LandingHero, type LandingHeroProps } from "./LandingHero";
export { TourIndex, type TourIndexProps } from "./TourIndex";
export { CaptureScene } from "./scenes/CaptureScene";
export { HomeScene } from "./scenes/HomeScene";
export { IngredientsScene } from "./scenes/IngredientsScene";
export { NotebooksScene } from "./scenes/NotebooksScene";
export { OverviewScene } from "./scenes/OverviewScene";
export { ShopScene } from "./scenes/ShopScene";
export { TogetherScene } from "./scenes/TogetherScene";
