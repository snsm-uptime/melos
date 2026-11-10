import { ArrowIcon, CameraIcon, ClipboardIcon, LinkIcon } from "@/app/icons";
import { Chip } from "@/components/Chip";
import { landingMessages } from "@/lib/i18n/landing";
import type { Locale } from "@/lib/i18n/locale";

import { FakeButton, inAt, MiniCard, popAt, Scene } from "./parts";

/** Capture (FR-006.1): pasted text becomes a draft with a vague salt and "2 unit large" onion. */
export function CaptureScene({ locale }: { locale: Locale }) {
  const t = landingMessages[locale].demo.capture;
  const sources = [
    { label: t.sourceText, icon: <ClipboardIcon />, chosen: true },
    { label: t.sourceLink, icon: <LinkIcon />, chosen: false },
    { label: t.sourcePhoto, icon: <CameraIcon />, chosen: false },
  ];
  return (
    <Scene>
      <div className="grid grid-cols-3 gap-2">
        {sources.map((source) => (
          <span
            key={source.label}
            className={`flex min-w-0 flex-col items-center gap-1 rounded-[var(--radius-md)] border bg-surface px-1 py-2 text-center [&_svg]:size-5 ${
              source.chosen ? `border-accent text-accent ${popAt(1)}` : "border-border text-muted"
            }`}
          >
            {source.icon}
            <span className="w-full truncate">{source.label}</span>
          </span>
        ))}
      </div>

      <div
        className={`flex flex-col rounded-[var(--radius-md)] border border-dashed border-field-border px-3 py-2 text-muted ${inAt(1)}`}
      >
        <span>{t.pastedSalt}</span>
        <span>{t.pastedOnion}</span>
      </div>

      <ArrowIcon className={`mx-auto size-4 rotate-90 text-muted ${inAt(2)}`} />

      <MiniCard title={t.draftTitle} className={inAt(2)}>
        <div className={`flex flex-wrap items-center gap-x-2 gap-y-1 ${inAt(3)}`}>
          <strong className="font-semibold">{t.salt}</strong>
          <span className="text-muted">{t.saltNote}</span>
          <Chip tone="warning">{t.vague}</Chip>
        </div>
        <div className={`flex flex-wrap items-center gap-x-2 ${inAt(4)}`}>
          <strong className="font-semibold">{t.onion}</strong>
          <span>{t.onionAmount}</span>
        </div>
        <FakeButton className={`mt-1 ${inAt(5)}`}>{t.review}</FakeButton>
      </MiniCard>
    </Scene>
  );
}
