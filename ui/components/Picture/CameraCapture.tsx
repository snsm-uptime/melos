"use client";

import { useEffect, useRef } from "react";

import { useCaptureMessages } from "@/lib/i18n/useCaptureMessages";

type CameraCaptureProps = {
  open: boolean;
  /** The photo taken from the live preview, as a JPEG file. */
  onCapture: (file: File) => void;
  /** The camera could not be opened (no camera, or permission refused). */
  onUnavailable: () => void;
  /** Told when the live preview starts (true) and when it stops (false). */
  onReadyChange: (ready: boolean) => void;
  /** Given the shutter while the preview is open (null when it closes), so the caller's button can take the photo. */
  onShutter: (take: (() => void) | null) => void;
};

/**
 * A live preview from the device camera (the webcam, or the phone's back camera). The caller's
 * own button takes the photo through `shutter`. Opens the stream when shown and stops it when
 * closed; the stream is never kept.
 */
export function CameraCapture({
  open,
  onCapture,
  onUnavailable,
  onReadyChange,
  onShutter,
}: CameraCaptureProps) {
  const t = useCaptureMessages();
  const video = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (!open) return;
    let stream: MediaStream | null = null;
    let cancelled = false;
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false })
      .then((media) => {
        if (cancelled) {
          media.getTracks().forEach((track) => track.stop());
          return;
        }
        stream = media;
        if (video.current) {
          video.current.srcObject = media;
          void video.current.play().catch(() => undefined);
        }
        onReadyChange(true);
      })
      .catch(() => {
        if (!cancelled) onUnavailable();
      });
    const element = video.current;
    return () => {
      cancelled = true;
      stream?.getTracks().forEach((track) => track.stop());
      if (element) element.srcObject = null;
      onReadyChange(false);
    };
  }, [open, onUnavailable, onReadyChange]);

  useEffect(() => {
    if (!open) return;
    onShutter(() => {
      const source = video.current;
      if (!source || !source.videoWidth) return;
      const canvas = document.createElement("canvas");
      canvas.width = source.videoWidth;
      canvas.height = source.videoHeight;
      canvas.getContext("2d")?.drawImage(source, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => {
          if (blob) onCapture(new File([blob], "camera.jpg", { type: "image/jpeg" }));
        },
        "image/jpeg",
        0.92,
      );
    });
    return () => onShutter(null);
  }, [open, onCapture, onShutter]);

  if (!open) return null;
  return (
    <video
      ref={video}
      autoPlay
      playsInline
      muted
      aria-label={t.pictureCamera}
      className="aspect-[4/3] w-full rounded-[0.75rem] bg-black object-cover"
    />
  );
}
