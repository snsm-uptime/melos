import { describe, expect, it } from "vitest";

import { checkLink, MAX_LINK_CHARS } from "./linkRules";

describe("checkLink", () => {
  it("adds https:// when the link has no scheme", () => {
    expect(checkLink("example.test/soup")).toEqual({ ok: true, url: "https://example.test/soup" });
  });

  it("keeps http and https links and trims spaces", () => {
    expect(checkLink("  http://example.test/a  ")).toEqual({ ok: true, url: "http://example.test/a" });
    expect(checkLink("HTTPS://Example.test/A")).toEqual({ ok: true, url: "HTTPS://Example.test/A" });
  });

  it("refuses an empty field", () => {
    expect(checkLink("")).toEqual({ ok: false, reason: "empty" });
    expect(checkLink("   ")).toEqual({ ok: false, reason: "empty" });
  });

  it.each(["example", "ftp://example.test/a", "javascript:alert(1)", "file:///etc/passwd", "https://", "lentil soup.test"])(
    "refuses %s as not a web link",
    (raw) => {
      expect(checkLink(raw)).toEqual({ ok: false, reason: "invalid" });
    },
  );

  it("refuses a link over 2,048 characters and accepts one at the limit", () => {
    const base = "https://example.test/";
    expect(checkLink(base + "a".repeat(MAX_LINK_CHARS - base.length))).toMatchObject({ ok: true });
    expect(checkLink(base + "a".repeat(MAX_LINK_CHARS))).toEqual({ ok: false, reason: "too_long" });
  });

  it("leaves ports and addresses to the api", () => {
    expect(checkLink("example.test:8080/a")).toMatchObject({ ok: true });
    expect(checkLink("http://[::1]/")).toMatchObject({ ok: true });
  });
});
