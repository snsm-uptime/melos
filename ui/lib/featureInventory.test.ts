import { describe, expect, it } from "vitest";

import {
  availableFeatures,
  featureGroups,
  features,
  groupsInOrder,
  plannedFeatures,
  type Localized,
} from "./featureInventory";

/** specs/075-landing-feature-tour/contracts/feature-inventory.md, invariants 1–6. */
describe("feature inventory", () => {
  it("has the six groups in the order a person uses the app", () => {
    expect(featureGroups).toHaveLength(6);
    expect(groupsInOrder().map((group) => [group.order, group.id])).toEqual([
      [1, "capture"],
      [2, "notebooks"],
      [3, "together"],
      [4, "shop"],
      [5, "ingredients"],
      [6, "home"],
    ]);
  });

  it("gives every feature a unique id", () => {
    const ids = features.map((feature) => feature.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("has every text in English and in Spanish (FR-013)", () => {
    const texts: [string, Localized][] = [
      ...featureGroups.flatMap((g): [string, Localized][] => [
        [`${g.id}.title`, g.title],
        [`${g.id}.lede`, g.lede],
      ]),
      ...features.flatMap((f): [string, Localized][] => [
        [`${f.id}.name`, f.name],
        [`${f.id}.summary`, f.summary],
      ]),
    ];
    const missing = texts
      .filter(([, text]) => !text.en?.trim() || !text.es?.trim())
      .map(([path]) => path);
    expect(missing).toEqual([]);
  });

  it("names at least one backlog story for every feature", () => {
    for (const feature of features) {
      expect(feature.stories.length, feature.id).toBeGreaterThan(0);
      for (const story of feature.stories) expect(story, feature.id).toMatch(/^S-\d{3}$/);
    }
  });

  it("never leaves a group section empty", () => {
    for (const group of featureGroups) {
      expect(availableFeatures(group.id).length, group.id).toBeGreaterThan(0);
    }
  });

  it("puts each feature in exactly one place: its group's list or the planned list (SC-001)", () => {
    for (const feature of features) {
      const inGroup = availableFeatures(feature.group).includes(feature);
      const inPlanned = plannedFeatures().includes(feature);
      expect(Number(inGroup) + Number(inPlanned), feature.id).toBe(1);
    }
  });

  it("names at least 20 available features (SC-002)", () => {
    const available = featureGroups.flatMap((group) => availableFeatures(group.id));
    expect(available.length).toBeGreaterThanOrEqual(20);
  });

  it("says shopping list, never shopping kitchen (FR-016)", () => {
    const all = JSON.stringify([featureGroups, features]);
    expect(all).not.toMatch(/shopping kitchen/i);
    expect(all).not.toMatch(/cocina de compras/i);
  });
});
