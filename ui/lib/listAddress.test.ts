import { describe, expect, it } from "vitest";

import { listAddress, readListAddress } from "./listAddress";

describe("listAddress", () => {
  it("reads page and q with safe defaults", () => {
    expect(readListAddress(new URLSearchParams("page=3&q=soup"))).toEqual({ page: 3, q: "soup" });
    expect(readListAddress(new URLSearchParams(""))).toEqual({ page: 1, q: "" });
    expect(readListAddress(new URLSearchParams("page=0"))).toEqual({ page: 1, q: "" });
    expect(readListAddress(new URLSearchParams("page=abc"))).toEqual({ page: 1, q: "" });
  });

  it("writes only what differs from the defaults", () => {
    expect(listAddress("/notebooks/n1", 1, "")).toBe("/notebooks/n1");
    expect(listAddress("/notebooks/n1", 2, "")).toBe("/notebooks/n1?page=2");
    expect(listAddress("/notebooks/n1", 1, "soup")).toBe("/notebooks/n1?q=soup");
    expect(listAddress("/notebooks/n1", 1, "   ")).toBe("/notebooks/n1");
  });

  it("keeps a query the address already has, such as from", () => {
    const base = "/notebooks/n1?from=%2Fkitchens%2Fk1";
    expect(listAddress(base, 1, "")).toBe(base);
    expect(listAddress(base, 2, "soup")).toBe("/notebooks/n1?from=%2Fkitchens%2Fk1&page=2&q=soup");
    expect(listAddress(`${base}&page=3&q=old`, 1, "")).toBe(base);
  });
});
