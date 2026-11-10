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
export { ComingSoon, type ComingSoonProps } from "./ComingSoon";
export { GroupSection, type GroupSectionProps } from "./GroupSection";
export { LandingHero, type LandingHeroProps } from "./LandingHero";
