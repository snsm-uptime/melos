import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { MIN_LOADING_MS, withMinimumLoading } from "./minimumLoading";

describe("withMinimumLoading", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it("holds a fast result until the minimum has passed", async () => {
    const done = vi.fn();
    void withMinimumLoading(Promise.resolve("rows")).then(done);
    await vi.advanceTimersByTimeAsync(MIN_LOADING_MS - 1);
    expect(done).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(done).toHaveBeenCalledWith("rows");
  });

  it("adds nothing to a slow result", async () => {
    const done = vi.fn();
    const slow = new Promise((resolve) => setTimeout(() => resolve("rows"), 800));
    void withMinimumLoading(slow).then(done);
    await vi.advanceTimersByTimeAsync(799);
    expect(done).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(done).toHaveBeenCalledWith("rows");
  });

  it("holds a failure too, and keeps it a failure", async () => {
    const failed = vi.fn();
    void withMinimumLoading(Promise.reject(new Error("no"))).catch(failed);
    await vi.advanceTimersByTimeAsync(MIN_LOADING_MS - 1);
    expect(failed).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(failed).toHaveBeenCalledOnce();
  });
});
