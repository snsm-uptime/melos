"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Cropper, { type Area, type Point } from "react-easy-crop";

import { CameraIcon, CloseIcon, ClipboardIcon, PencilIcon, TrashIcon, UploadIcon } from "@/app/icons";
import { ActionDialog } from "@/components/ActionDialog";
import { FormIconSubmit } from "@/components/FormIconSubmit/FormIconSubmit";
import { IconButton } from "@/components/IconButton";
import { NotebookPicker } from "@/components/NotebookPicker";
import { CameraCapture } from "@/components/Picture/CameraCapture";
import { PictureProgress } from "@/components/Picture/PictureProgress";
import { photoActionClass } from "@/components/photoAction";
import { Tooltip } from "@/components/Tooltip";
import { ToggleSwitch } from "@/components/ToggleSwitch/ToggleSwitch";
import { BaseButton } from "@/components/soft-ledger/BaseButton";
import { submitPictureCapture } from "@/lib/capture/captureClient";
import {
  closeSheet,
  failSubmit,
  setHandwritten,
  setPicture,
  showDraft,
  startSubmit,
  useCaptureState,
} from "@/lib/capture/captureStore";
import { cropPictureFile } from "@/lib/capture/pictureCrop";
import { checkPicture } from "@/lib/capture/pictureRules";
import { messageForCode } from "@/lib/i18n/capture";
import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";
import { useLocale } from "@/lib/i18n/useLocale";

import type { CaptureCandidate } from "./AddRecipeCallToAction";
import { captureTarget, chooseNotebook, pickerOptions } from "./captureNotebook";
import { toDraftView } from "./TextCaptureSheet";

type PictureCaptureSheetProps = {
  open: boolean;
  candidates: CaptureCandidate[];
  onDraftReady: () => void;
};

/** The file types the picker offers (spec 041). The gallery and files; the camera has its own button. */
const ACCEPT = "image/jpeg,image/png,image/heic,image/heif,.heic,.heif";

/** The picture's frame: the same 4:3 rectangle as the picture itself. */
const FRAME_ASPECT = 4 / 3;

function sizeLabel(bytes: number): string {
  return bytes >= 1_000_000 ? `${(bytes / 1_000_000).toFixed(1)} MB` : `${Math.round(bytes / 1000)} KB`;
}

function isImage(item: File): boolean {
  return item.type.startsWith("image/") || /\.(heic|heif)$/i.test(item.name);
}

/**
 * Position and zoom the picture, as the profile picture does (react-easy-crop, zoom 1 to 3).
 * Remounted for each picture, so framing starts fresh.
 */
function PictureEditor({
  src,
  saveLabel,
  zoomLabel,
  busy,
  onSave,
}: {
  src: string;
  saveLabel: string;
  zoomLabel: string;
  busy: boolean;
  onSave: (area: Area) => void;
}) {
  const [crop, setCrop] = useState<Point>({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [area, setArea] = useState<Area | null>(null);

  return (
    <div className="flex flex-col gap-3">
      <div className="relative aspect-[4/3] w-full overflow-hidden rounded-[0.75rem] bg-surface">
        <Cropper
          image={src}
          crop={crop}
          zoom={zoom}
          aspect={FRAME_ASPECT}
          cropShape="rect"
          onCropChange={setCrop}
          onZoomChange={setZoom}
          onCropComplete={(_, pixels) => setArea(pixels)}
        />
        {/* The save icon takes the top-left corner while the picture is edited. */}
        <FormIconSubmit
          type="button"
          variant="save"
          label={saveLabel}
          disabled={!area || busy}
          onClick={() => {
            if (area) onSave(area);
          }}
          className="absolute top-2 left-2 z-10"
        />
      </div>
      <input
        type="range"
        aria-label={zoomLabel}
        min={1}
        max={3}
        step={0.1}
        value={zoom}
        onChange={(event) => setZoom(Number(event.target.value))}
        className="w-full"
      />
    </div>
  );
}

/**
 * The picture capture modal (spec 041). The top is the form: the icon buttons on the left, the
 * switch with its label, and Read recipe at the end of the row; then the notebook picker, the drop
 * card while no picture is chosen, messages and progress. The bottom is the picture, with a pencil
 * (position and zoom it) and a trash (remove it) on its corners. While it is edited, the save icon
 * takes the top-left corner and the cropper replaces the picture.
 */
export function PictureCaptureSheet({ open, candidates, onDraftReady }: PictureCaptureSheetProps) {
  const t = useCaptureMessages();
  const locale = useLocale();
  const capture = useCaptureState();
  const inputRef = useRef<HTMLInputElement>(null);

  const notebook = capture.notebook;
  const source = capture.source.kind === "picture" ? capture.source : null;
  const file = source?.file ?? null;
  const handwritten = source?.handwritten ?? true;
  const submitting = capture.phase === "submitting";
  const options = pickerOptions(candidates, notebook);

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [imageFailed, setImageFailed] = useState(false);
  const [fieldMessage, setFieldMessage] = useState<string | null>(null);
  const [positioning, setPositioning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [cameraReady, setCameraReady] = useState(false);
  const shutter = useRef<(() => void) | null>(null);
  const setShutter = useCallback((take: (() => void) | null) => {
    shutter.current = take;
  }, []);

  // The preview is an object URL for the chosen file: made on choice, revoked on change and unmount.
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the object URL lives outside React; one render per file
    setPreviewUrl(url);
    setImageFailed(false);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const shownPreview = file ? previewUrl : null;

  const chooseRef = useRef<(files: FileList | File[]) => Promise<void>>(async () => {});
  useEffect(() => {
    chooseRef.current = choose;
  });

  // Paste an image from the clipboard while the sheet is open and idle.
  useEffect(() => {
    if (!open || submitting) return;
    function onPaste(event: ClipboardEvent) {
      const images = Array.from(event.clipboardData?.files ?? []).filter(isImage);
      if (images.length === 0) return;
      event.preventDefault();
      void chooseRef.current(images);
    }
    document.addEventListener("paste", onPaste);
    return () => document.removeEventListener("paste", onPaste);
  }, [open, submitting]);

  async function choose(files: FileList | File[]) {
    const list = Array.from(files);
    if (list.length === 0) return;
    if (list.length > 1) {
      setFieldMessage(t.pictureOneAtATime);
      return;
    }
    const [picked] = list;
    const check = await checkPicture(picked);
    if (!check.ok) {
      // The previous choice stays; only the message changes.
      setFieldMessage(check.reason === "too_large" ? t.pictureTooLarge : t.pictureUnsupported);
      return;
    }
    setFieldMessage(null);
    setPositioning(false);
    setPicture(picked);
  }

  /** The camera button: a live view from the webcam or phone camera; a file when there is none. */
  function openCamera() {
    if (typeof navigator.mediaDevices?.getUserMedia === "function") {
      setCameraOpen(true);
      return;
    }
    setFieldMessage(t.pictureCameraOff);
  }

  const onCameraUnavailable = useCallback(() => {
    setCameraOpen(false);
    setFieldMessage(t.pictureCameraOff);
  }, [t.pictureCameraOff]);

  const onCameraShot = useCallback(
    (shot: File) => {
      setCameraOpen(false);
      void chooseRef.current([shot]);
    },
    [],
  );

  function remove() {
    setFieldMessage(null);
    setPositioning(false);
    setPicture(null);
  }

  /** Save the framing: the cropped picture replaces the chosen one, which is then sent as usual. */
  async function saveFraming(area: Area) {
    if (!file || saving) return;
    setSaving(true);
    try {
      const cropped = await cropPictureFile(file, area);
      setPicture(cropped);
      setPositioning(false);
    } catch {
      setFieldMessage(t.pictureUnsupported);
    } finally {
      setSaving(false);
    }
  }

  async function submit() {
    if (!notebook || !file || submitting) return;
    startSubmit();
    const target = await captureTarget(notebook);
    if (!target.ok) {
      failSubmit({ code: target.code });
      return;
    }
    const result = await submitPictureCapture(target.notebook.id, file, handwritten);
    if (!result.ok) {
      failSubmit(result.message);
      return;
    }
    showDraft({ ...toDraftView(result.value), fromPicture: true }, result.value.language);
    onDraftReady();
  }

  const serverMessage = capture.message
    ? messageForCode(capture.message, locale, undefined, "picture")
    : null;
  const message = serverMessage ?? fieldMessage;

  const top = (
    <form
      className="flex flex-col gap-4"
      noValidate
      onDragOver={(event) => event.preventDefault()}
      onDrop={(event) => {
        event.preventDefault();
        void choose(event.dataTransfer.files);
      }}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
    >
      {/* Row 2: icon buttons, then the switch and its label, then Read recipe at the end. While the
          camera is open, the row becomes two equal columns: close, and take the photo. */}
      {cameraOpen ? (
        // The landing page's buttons, with the colours of this sheet: close is a violet outline,
        // the camera an orange fill whose icon takes the background colour.
        <div className="flex items-center gap-2">
          <BaseButton
            variant="ghost"
            className="flex-1"
            style={{ "--accent": "var(--primary)" } as React.CSSProperties}
            aria-label={t.close}
            onClick={() => setCameraOpen(false)}
          >
            <CloseIcon className="size-5" />
          </BaseButton>
          <BaseButton
            variant="accent"
            className="flex-1"
            style={
              {
                "--secondary": "var(--accent-fill)",
                "--on-secondary": "var(--surface)",
              } as React.CSSProperties
            }
            aria-label={t.pictureShoot}
            disabled={!cameraReady}
            onClick={() => shutter.current?.()}
          >
            <CameraIcon className="size-5" />
          </BaseButton>
        </div>
      ) : (
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          <IconButton
            variant="ghost"
            label={t.pictureCamera}
            icon={<CameraIcon className="size-5" />}
            disabled={submitting}
            onClick={openCamera}
          />
          {/* Not clickable: its tooltip says to paste. aria-disabled, not disabled, so hover still works. */}
          <IconButton
            variant="ghost"
            label={t.pictureClipboardHint}
            icon={<ClipboardIcon className="size-5" />}
            aria-disabled="true"
            className="cursor-default opacity-60"
            onClick={(event) => event.preventDefault()}
          />
        </div>
        <div className="flex items-center gap-2">
          <ToggleSwitch
            checked={handwritten}
            disabled={submitting}
            label={t.pictureHandwritten}
            onChange={(on) => setHandwritten(on)}
          />
          <span className="text-[0.9rem] text-foreground">
            {handwritten ? t.pictureHandwritten : t.pictureTyped}
          </span>
        </div>
        <BaseButton
          variant="primary"
          type="submit"
          disabled={!file || submitting || notebook === null}
          loading={submitting}
        >
          {t.pictureSubmit}
        </BaseButton>
      </div>

      )}

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="sr-only"
        aria-label={t.pictureChoose}
        disabled={submitting}
        onChange={(event) => {
          void choose(event.target.files ?? []);
          event.target.value = "";
        }}
      />

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

      {!file && !cameraOpen ? (
        <button
          type="button"
          aria-label={t.pictureDrop}
          disabled={submitting}
          onClick={() => inputRef.current?.click()}
          className="flex min-h-28 w-full cursor-pointer items-center justify-center rounded-[var(--radius-md)] border border-border bg-surface text-muted transition-[color,border-color,box-shadow,transform] duration-150 enabled:hover:-translate-y-0.5 enabled:hover:border-accent enabled:hover:text-accent enabled:hover:shadow-elevation-1 focus-visible:border-accent focus-visible:text-accent disabled:cursor-not-allowed disabled:opacity-65 motion-reduce:transition-none motion-reduce:hover:translate-y-0"
        >
          <UploadIcon className="size-8" />
          <span className="sr-only">{t.pictureDrop}</span>
        </button>
      ) : null}

      {message && !submitting ? (
        <p role="alert" className="m-0 text-[0.9rem] text-error">
          {message}
        </p>
      ) : null}

      {submitting ? <PictureProgress handwritten={handwritten} /> : null}
    </form>
  );

  // The bottom section: the picture with its corner actions, or the editor while it is edited.
  const bottom = cameraOpen ? (
    <CameraCapture
      open={cameraOpen}
      onCapture={onCameraShot}
      onUnavailable={onCameraUnavailable}
      onReadyChange={setCameraReady}
      onShutter={setShutter}
    />
  ) : file && shownPreview ? (
      positioning ? (
        <PictureEditor
          key={shownPreview}
          src={shownPreview}
          saveLabel={t.pictureSave}
          zoomLabel={t.pictureZoom}
          busy={saving}
          onSave={(area) => void saveFraming(area)}
        />
      ) : (
        <figure className="relative m-0">
          {imageFailed ? (
            <p className="m-0 rounded-[0.75rem] border border-field-border p-4 text-[0.9rem] text-muted">
              {t.pictureFileLabel(file.name, sizeLabel(file.size))}
            </p>
          ) : (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={shownPreview}
              alt={t.picturePreviewAlt}
              onError={() => setImageFailed(true)}
              className="block aspect-[4/3] w-full rounded-[0.75rem] object-cover"
            />
          )}
          {/* The profile picture's corners: edit on the bottom-left, remove on the top-right. */}
          <button
            type="button"
            aria-label={t.pictureEdit}
            className={`${photoActionClass} bottom-2 left-2 size-8`}
            disabled={submitting}
            onClick={() => setPositioning(true)}
          >
            <Tooltip label={t.pictureEdit}>
              <PencilIcon className="size-4" />
            </Tooltip>
          </button>
          <button
            type="button"
            aria-label={t.pictureRemove}
            className={`${photoActionClass} top-2 right-2 size-8 text-error`}
            disabled={submitting}
            onClick={remove}
          >
            <Tooltip label={t.pictureRemove}>
              <TrashIcon className="size-4" />
            </Tooltip>
          </button>
        </figure>
      )
    ) : null;

  return (
    <ActionDialog
      open={open}
      onOpenChange={(next) => {
        if (!next) closeSheet();
      }}
      closeLabel={t.close}
      title={notebook?.name ?? t.pictureTitle}
    >
      <div className="flex flex-col gap-5">
        {top}
        {bottom}
      </div>
    </ActionDialog>
  );
}
