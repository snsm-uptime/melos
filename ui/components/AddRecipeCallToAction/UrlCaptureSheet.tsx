"use client";

import { NotebookPicker } from "@/components/NotebookPicker";
import { Sheet } from "@/app/kitchens/Sheet";
import { CauldronLoader } from "@/components/CauldronLoader";
import { submitLinkCapture } from "@/lib/capture/captureClient";
import {
  closeSheet,
  failSubmit,
  setLink,
  showDraft,
  startSubmit,
  useCaptureState,
} from "@/lib/capture/captureStore";
import { checkLink } from "@/lib/capture/linkRules";
import { messageForCode } from "@/lib/i18n/capture";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";
import { useLocale } from "@/lib/i18n/useLocale";

import type { CaptureCandidate } from "./AddRecipeCallToAction";
import {
  captureTarget,
  chooseNotebook,
  pickerOptions,
} from "./captureNotebook";
import { toDraftView } from "./TextCaptureSheet";

type UrlCaptureSheetProps = {
  open: boolean;
  candidates: CaptureCandidate[];
  onDraftReady: () => void;
};

const fieldClassName =
  "w-full rounded-[0.75rem] border border-border bg-background px-3 py-2 text-[0.95rem] text-foreground";

/**
 * The link sheet (spec 026 FR-001 to FR-004, FR-018, FR-023): one link field, the notebook
 * picker, and Read recipe. The link stays in the store, so a refusal or Back keeps it unchanged.
 * One submission at a time; the api opens the page, never the browser.
 */
export function UrlCaptureSheet({
  open,
  candidates,
  onDraftReady,
}: UrlCaptureSheetProps) {
  const t = useCaptureMessages();
  const locale = useLocale();
  const capture = useCaptureState();

  const notebook = capture.notebook;
  const link = capture.source.kind === "url" ? capture.source.link : "";
  const check = checkLink(link);
  const submitting = capture.phase === "submitting";
  const disabled = !check.ok || submitting || notebook === null;
  const options = pickerOptions(candidates, notebook);

  async function submit() {
    if (!notebook || disabled || !check.ok) return;
    startSubmit();
    const target = await captureTarget(notebook);
    if (!target.ok) {
      failSubmit({ code: target.code });
      return;
    }
    const result = await submitLinkCapture(target.notebook.id, check.url);
    if (!result.ok) {
      failSubmit(result.message);
      return;
    }
    showDraft(toDraftView(result.value), result.value.language);
    onDraftReady();
  }

  // The field message for a link the button refuses; an empty field shows nothing.
  const fieldMessage =
    !check.ok && check.reason === "invalid"
      ? t.linkInvalid
      : !check.ok && check.reason === "too_long"
        ? t.linkTooLong
        : null;
  const message = capture.message
    ? messageForCode(capture.message, locale, undefined, "url")
    : fieldMessage;

  const body = (
    <form
      className="flex flex-col gap-4"
      // The browser's own URL check would block "example.test/soup", which the link rules accept
      // by adding https://. The link rules decide, and show their own messages.
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {candidates.length > 1 && notebook ? (
        <div className="flex flex-col gap-1 text-[0.85rem] text-muted">
          <span aria-hidden="true">{t.notebookPicker}</span>
          <NotebookPicker
            locale={locale}
            label={t.notebookPicker}
            value={notebook.id}
            disabled={submitting}
            notebooks={options}
            onChange={(id) => chooseNotebook(options, id, notebook)}
          />
        </div>
      ) : null}
      <label className="flex flex-col gap-1 text-[0.85rem] text-muted">
        {t.linkLabel}
        <input
          type="url"
          inputMode="url"
          autoComplete="url"
          spellCheck={false}
          className={fieldClassName}
          placeholder={t.linkPlaceholder}
          value={link}
          readOnly={submitting}
          aria-invalid={message ? true : undefined}
          onChange={(event) => setLink(event.target.value)}
        />
      </label>
      {message && !submitting ? (
        <p role="alert" className="m-0 text-[0.9rem] text-error">
          {message}
        </p>
      ) : null}
      <button
        type="submit"
        disabled={disabled}
        aria-busy={submitting || undefined}
        className="inline-flex items-center gap-2 self-end rounded-[0.75rem] bg-accent px-4 py-2 text-[0.95rem] text-background disabled:opacity-50"
      >
        {/* The wait shows on the button itself; its text already says what is happening. */}
        {submitting ? <CauldronLoader tone="button" /> : null}
        <span>{submitting ? t.submittingLink : t.submit}</span>
      </button>
    </form>
  );

  return (
    <Sheet
      open={open}
      onClose={closeSheet}
      closeLabel={t.close}
      title={notebook?.name ?? t.addRecipe}
      body={body}
    />
  );
}
