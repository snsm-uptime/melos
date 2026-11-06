/** @vitest-environment jsdom */

import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ShareRecipeDialog } from "./ShareRecipeDialog";

const CANDIDATES = [
  { user_id: "u-ben", alias: "Ben" },
  { user_id: "u-ana", alias: "Ana" },
];

/** Fetch answers by URL: the candidate list at once, the send when the test releases it. */
function stubApi(sendReply: (url: string, init?: RequestInit) => Promise<Response>) {
  const send = vi.fn(sendReply);
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (String(url).endsWith("/share-candidates")) {
        return new Response(JSON.stringify({ candidates: CANDIDATES }), { status: 200 });
      }
      return send(url, init);
    }),
  );
  return send;
}

function gatedSend(status: number, body: unknown) {
  let finish: () => void = () => {};
  const gate = new Promise<void>((resolve) => (finish = resolve));
  const reply = async () => {
    await gate;
    return new Response(JSON.stringify(body), { status });
  };
  return { reply, finish };
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("ShareRecipeDialog", () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
  });

  afterEach(() => {
    act(() => root.unmount());
    container.remove();
    vi.unstubAllGlobals();
    document.body.innerHTML = "";
  });

  async function open() {
    await act(async () => {
      root.render(
        <ShareRecipeDialog recipeId="r-1" locale="en" open onOpenChange={() => {}} />,
      );
    });
    await act(async () => {
      await flush();
    });
  }

  const sendButton = () =>
    document.querySelector<HTMLButtonElement>('button[aria-label="Send recipe"]')!;
  const combobox = () => document.querySelector<HTMLButtonElement>('[role="combobox"]')!;

  async function choose(alias: string) {
    act(() => combobox().click());
    const option = Array.from(document.querySelectorAll<HTMLElement>('[role="option"]')).find(
      (o) => o.textContent === alias,
    )!;
    act(() => option.click());
  }

  it("keeps send disabled until a person is chosen", async () => {
    stubApi(async () => new Response("{}", { status: 201 }));
    await open();
    expect(sendButton().disabled).toBe(true);
    await choose("Ben");
    expect(sendButton().disabled).toBe(false);
  });

  it("sends once per press and shows success naming the person", async () => {
    const gate = gatedSend(201, { recipe_id: "c-1", recipient_alias: "Ben", notebook_id: "n-1" });
    const send = stubApi(gate.reply);
    await open();
    await choose("Ben");

    act(() => sendButton().click());
    act(() => sendButton().click());
    expect(sendButton().disabled).toBe(true);

    await act(async () => {
      gate.finish();
      await flush();
    });

    expect(send).toHaveBeenCalledTimes(1);
    const [url, init] = send.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/recipes/r-1/share");
    expect(JSON.parse(String(init.body))).toEqual({ recipient_user_id: "u-ben" });
    expect(document.querySelector('[role="status"]')?.textContent).toContain("Ben");
    expect(document.querySelector('[role="combobox"]')).toBeNull();
  });

  it("keeps the selection and shows the message after an error", async () => {
    const gate = gatedSend(404, { code: "recipient_not_found" });
    stubApi(gate.reply);
    await open();
    await choose("Ana");

    act(() => sendButton().click());
    await act(async () => {
      gate.finish();
      await flush();
    });

    expect(document.querySelector('[role="alert"]')?.textContent).toBe(
      "That person can't be found.",
    );
    expect(combobox().textContent).toContain("Ana");
    expect(sendButton().disabled).toBe(false);
  });

  it("explains when there is no one to share with", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ candidates: [] }), { status: 200 })),
    );
    await open();
    expect(document.body.textContent).toContain("Share a kitchen or a recipe book");
  });
});
