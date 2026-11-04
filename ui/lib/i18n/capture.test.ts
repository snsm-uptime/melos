import { describe, expect, it } from "vitest";

import type { CaptureMessage } from "../capture/captureStore";
import { captureMessagesFor, captureText, messageForCode } from "./capture";

const captureMessages = captureMessagesFor("en");

describe("messageForCode", () => {
  it.each<[string, CaptureMessage, string]>([
    ["one_recipe_at_a_time", { code: "one_recipe_at_a_time" }, captureMessages.oneRecipe],
    ["ai_invalid_output", { code: "ai_invalid_output" }, captureMessages.invalidOutput],
    ["ai_limit_reached", { code: "ai_limit_reached" }, captureMessages.limit],
    ["ai_misconfigured", { code: "ai_misconfigured" }, captureMessages.misconfigured],
    ["kitchen_archived", { code: "kitchen_archived" }, captureMessages.archived],
    ["notebook_not_found", { code: "notebook_not_found" }, captureMessages.notFound],
  ])("%s returns its own fixed message", (_name, message, expected) => {
    expect(messageForCode(message, "en")).toBe(expected);
  });

  it("text_too_long names the limit", () => {
    expect(messageForCode({ code: "text_too_long" }, "en", 5000)).toBe(captureMessages.tooLong(5000));
  });

  it.each<[string, CaptureMessage]>([
    ["draft_incomplete", { code: "draft_incomplete", missing: ["title"] }],
    ["ingredient_line_problem", { code: "ingredient_line_problem", lineProblems: [{ name: "butter", kind: "unit_missing" }] }],
  ])("%s returns a non-empty message", (_name, message) => {
    expect(messageForCode(message, "en").length).toBeGreaterThan(0);
  });

  it("not_a_recipe reasons each give their own message", () => {
    const reasons = ["question_or_request", "not_food", "story_or_article"];
    const messages = reasons.map((reason) => messageForCode({ code: "not_a_recipe", reason, ingredient: null }, "en"));

    expect(new Set(messages).size).toBe(reasons.length);
    for (const message of messages) {
      expect(message).not.toBe(captureMessages.unavailable);
    }
  });

  it("ai_unavailable is the only code that uses the generic fallback", () => {
    expect(messageForCode({ code: "ai_unavailable" }, "en")).toBe(captureMessages.unavailable);
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
      expect(messageForCode(message, "en", 5000)).not.toBe(captureMessages.unavailable);
    }
  });
});

describe("Spanish capture messages (spec 063)", () => {
  const codes: CaptureMessage[] = [
    { code: "not_a_recipe", reason: "question_or_request", ingredient: null },
    { code: "not_a_recipe", reason: "not_food", ingredient: null },
    { code: "not_a_recipe", reason: "story_or_article", ingredient: null },
    { code: "not_a_recipe" },
    { code: "one_recipe_at_a_time" },
    { code: "draft_incomplete", missing: ["title", "steps"] },
    {
      code: "ingredient_line_problem",
      lineProblems: [
        { name: "butter", kind: "unit_missing" },
        { name: "flour", kind: "quantity_missing" },
        { name: "salt", kind: "unit_not_recognized" },
      ],
    },
    { code: "ai_invalid_output" },
    { code: "text_too_long" },
    { code: "ai_limit_reached" },
    { code: "ai_misconfigured" },
    { code: "kitchen_archived" },
    { code: "notebook_gone" },
    { code: "invalid_recipe" },
    { code: "save_unavailable" },
    { code: "notebook_not_found" },
    { code: "ai_unavailable" },
  ];

  it.each(codes.map((message) => [message.code + (message.reason ? `/${message.reason}` : ""), message] as const))(
    "%s has a Spanish message different from the English one",
    (_name, message) => {
      const en = messageForCode(message, "en", 5000);
      const es = messageForCode(message, "es", 5000);
      expect(es.length).toBeGreaterThan(0);
      expect(es).not.toBe(en);
    },
  );

  it("names the same missing parts and lines in Spanish", () => {
    const text = messageForCode(
      {
        code: "ingredient_line_problem",
        missing: ["title", "steps"],
        lineProblems: [{ name: "butter", kind: "unit_missing" }],
      },
      "es",
    );
    expect(text).toContain("título");
    expect(text).toContain("pasos");
    expect(text).toContain("butter");
  });

  it("names the limit and an ingredient in Spanish", () => {
    expect(messageForCode({ code: "text_too_long" }, "es", 4000)).toContain("4000");
    expect(
      messageForCode({ code: "not_a_recipe", reason: "question_or_request", ingredient: "sal" }, "es"),
    ).toContain("sal");
  });

  it("has a Spanish message for every key and the same function arity", () => {
    const en = captureText.en as Record<string, unknown>;
    const es = captureText.es as Record<string, unknown>;
    expect(Object.keys(es).sort()).toEqual(Object.keys(en).sort());
    for (const key of Object.keys(en)) {
      if (typeof en[key] === "function") expect((es[key] as () => void).length).toBe((en[key] as () => void).length);
    }
  });

  it("captureMessagesFor returns the chosen language", () => {
    expect(captureMessagesFor("es").save).toBe("Guardar receta");
    expect(captureMessagesFor("en").save).toBe("Save recipe");
  });
});
