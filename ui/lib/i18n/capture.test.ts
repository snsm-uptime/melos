import { describe, expect, it } from "vitest";

import type { CaptureMessage } from "../capture/captureStore";
import { captureMessages, messageForCode } from "./capture";

describe("messageForCode", () => {
  it.each<[string, CaptureMessage, string]>([
    ["one_recipe_at_a_time", { code: "one_recipe_at_a_time" }, captureMessages.oneRecipe],
    ["ai_invalid_output", { code: "ai_invalid_output" }, captureMessages.invalidOutput],
    ["ai_limit_reached", { code: "ai_limit_reached" }, captureMessages.limit],
    ["ai_misconfigured", { code: "ai_misconfigured" }, captureMessages.misconfigured],
    ["kitchen_archived", { code: "kitchen_archived" }, captureMessages.archived],
    ["notebook_not_found", { code: "notebook_not_found" }, captureMessages.notFound],
  ])("%s returns its own fixed message", (_name, message, expected) => {
    expect(messageForCode(message)).toBe(expected);
  });

  it("text_too_long names the limit", () => {
    expect(messageForCode({ code: "text_too_long" }, 5000)).toBe(captureMessages.tooLong(5000));
  });

  it.each<[string, CaptureMessage]>([
    ["draft_incomplete", { code: "draft_incomplete", missing: ["title"] }],
    ["ingredient_line_problem", { code: "ingredient_line_problem", lineProblems: [{ name: "butter", kind: "unit_missing" }] }],
  ])("%s returns a non-empty message", (_name, message) => {
    expect(messageForCode(message).length).toBeGreaterThan(0);
  });

  it("not_a_recipe reasons each give their own message", () => {
    const reasons = ["question_or_request", "not_food", "story_or_article"];
    const messages = reasons.map((reason) => messageForCode({ code: "not_a_recipe", reason, ingredient: null }));

    expect(new Set(messages).size).toBe(reasons.length);
    for (const message of messages) {
      expect(message).not.toBe(captureMessages.unavailable);
    }
  });

  it("ai_unavailable is the only code that uses the generic fallback", () => {
    expect(messageForCode({ code: "ai_unavailable" })).toBe(captureMessages.unavailable);
  });

  it("no refusal code other than ai_unavailable returns the generic fallback", () => {
    const codes: CaptureMessage[] = [
      { code: "not_a_recipe", reason: "not_food", ingredient: null },
      { code: "one_recipe_at_a_time" },
      { code: "draft_incomplete", missing: ["steps"] },
      { code: "ingredient_line_problem", lineProblems: [{ name: null, kind: "quantity_missing" }] },
      { code: "ai_invalid_output" },
      { code: "text_too_long" },
      { code: "ai_limit_reached" },
      { code: "ai_misconfigured" },
      { code: "kitchen_archived" },
      { code: "notebook_not_found" },
    ];

    for (const message of codes) {
      expect(messageForCode(message, 5000)).not.toBe(captureMessages.unavailable);
    }
  });
});
