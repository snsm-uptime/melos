"use client";

import {
  FormEvent,
  KeyboardEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useRouter } from "next/navigation";

import { Chip } from "@/components/Chip";
import { IconButton } from "@/components/IconButton";
import {
  IconButtonPopup,
  IconButtonPopupItem,
} from "@/components/IconButtonPopup";
import { usePreferences } from "@/components/PreferencesProvider";
import { StackedListPanel } from "@/components/StackedListPanel";
import { GhostButton } from "@/components/soft-ledger/GhostButton";
import { GhostInput } from "@/components/soft-ledger/GhostInput";
import { GhostTextField } from "@/components/soft-ledger/GhostTextField";
import { kitchensMessages } from "@/lib/i18n/kitchens";
import {
  ArchiveToggleIcon,
  DotsIcon,
  PencilIcon,
  PlusIcon,
  TrashIcon,
  UsersIcon,
  WalletIcon,
} from "@/app/icons";
import type { InviteFormMessages } from "./InviteForm";
import { InviteForm } from "./InviteForm";
import { Sheet } from "./Sheet";
import {
  archiveKitchen,
  createKitchen,
  deleteKitchen,
  fetchKitchens,
  hideKitchen,
  memberLabel,
  renameKitchen,
  setLastOpenedKitchen,
  unarchiveKitchen,
  unhideKitchen,
  type KitchenItem,
} from "./kitchensClient";
import {
  patchMembershipKitchens,
  replaceMembershipKitchens,
  useMembershipKitchens,
} from "./membershipKitchensStore";
import styles from "./kitchens.module.scss";

function rosterForCard(kitchen: KitchenItem, currentUserId: string) {
  return [...(kitchen.members ?? [])]
    .filter((member) => member.user_id !== currentUserId)
    .sort((a, b) =>
      memberLabel(a).localeCompare(memberLabel(b), undefined, {
        sensitivity: "base",
      }),
    );
}

function Pulse({ className }: { className: string }) {
  return <div className={`animate-pulse rounded-md bg-muted ${className}`} />;
}

function ArchivedKitchensSkeleton() {
  return (
    <div
      className={styles.list}
      role="status"
      aria-live="polite"
      aria-label="Loading archived kitchens"
    >
      {[0, 1, 2].map((i) => (
        <div key={i} className={styles.row}>
          <div className={styles.cardShell}>
            <div className={styles.cardBody}>
              <span className={styles.cardFace}>
                <Pulse className="h-5 w-5 shrink-0 rounded-full" />
                <span className={styles.cardFaceMain}>
                  <Pulse className="h-4 w-2/5" />
                  <Pulse className="h-3 w-1/4" />
                </span>
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function KitchenRoleBookmark({ label, icon }: { label: string; icon: ReactNode }) {
  return (
    <span className={`${styles.roleBookmark} px-3`} aria-label={label}>
      {icon}
    </span>
  );
}

function KitchenCardFace({
  kitchen,
  currentUserId,
  isOwner,
  title,
  memberBadge,
  ownerBadge,
}: {
  kitchen: KitchenItem;
  currentUserId: string;
  isOwner: boolean;
  title: ReactNode;
  memberBadge: string;
  ownerBadge: string;
}) {
  const roster = rosterForCard(kitchen, currentUserId);
  const hasRoster = roster.length > 0;
  return (
    <span className={styles.cardFace}>
      {isOwner ? (
        <KitchenRoleBookmark
          label={ownerBadge}
          icon={<WalletIcon className={styles.roleBookmarkIcon} />}
        />
      ) : (
        <KitchenRoleBookmark
          label={memberBadge}
          icon={<UsersIcon className={styles.roleBookmarkIcon} />}
        />
      )}
      <span className={styles.cardFaceMain}>
        {title}
        {hasRoster ? (
          <span className={styles.chipRow}>
            {roster.map((member) => (
              <Chip
                key={member.user_id}
                tone={member.user_id === kitchen.owner_id ? "accent" : "muted"}
              >
                {memberLabel(member)}
              </Chip>
            ))}
          </span>
        ) : null}
      </span>
    </span>
  );
}

type Props = {
  initialKitchens: KitchenItem[];
  currentUserId: string;
  showArchived?: boolean;
};

export function KitchensPanel({ initialKitchens, currentUserId, showArchived = false }: Props) {
  const { locale } = usePreferences();
  const t = kitchensMessages[locale];
  const router = useRouter();
  const [archivedKitchens, setArchivedKitchens] = useState<KitchenItem[]>([]);
  const [archivedLoading, setArchivedLoading] = useState(false);
  const [archivedLoadError, setArchivedLoadError] = useState<string | null>(null);
  const [archiveActionError, setArchiveActionError] = useState<string | null>(null);
  const [archivingId, setArchivingId] = useState<string | null>(null);
  const createNameId = useId();
  const [newName, setNewName] = useState("");
  const [createError, setCreateError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const creatingRef = useRef(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [renameDrafts, setRenameDrafts] = useState<Record<string, string>>({});
  const [renameErrors, setRenameErrors] = useState<Record<string, string>>({});
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [invitingKitchenId, setInvitingKitchenId] = useState<string | null>(null);
  const renameInputRef = useRef<HTMLInputElement | null>(null);
  const renamingIdRef = useRef<string | null>(null);

  const messages = useMemo(
    () => ({
      errorGeneric: t.errorGeneric,
      errorInvalidName: t.errorInvalidName,
      errorForbidden: t.errorForbidden,
      errorUnauthorized: t.errorUnauthorized,
      inviteTitle: t.inviteTitle,
      inviteLabel: t.inviteLabel,
      inviteSubmit: t.inviteSubmit,
      inviteSending: t.inviteSending,
      inviteSent: t.inviteSent,
    }),
    [t],
  ) as InviteFormMessages;

  const canCreate = newName.trim().length > 0 && !creating;

  const closeInviteSheet = useCallback(() => setInvitingKitchenId(null), []);

  useLayoutEffect(() => {
    replaceMembershipKitchens(initialKitchens);
  }, [initialKitchens]);

  const membershipKitchens = useMembershipKitchens() ?? initialKitchens;
  const kitchens = showArchived ? archivedKitchens : membershipKitchens;

  useEffect(() => {
    if (!showArchived) return;
    let cancelled = false;
    async function loadArchived() {
      setArchivedLoading(true);
      const result = await fetchKitchens(messages, { archived: true });
      if (cancelled) return;
      if (result.ok) {
        setArchivedLoadError(null);
        setArchivedKitchens(result.kitchens);
      } else {
        setArchivedLoadError(result.error);
        setArchivedKitchens([]);
      }
      setArchivedLoading(false);
    }
    void loadArchived();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showArchived]);

  useEffect(() => {
    if (!editingId) return;
    const input = renameInputRef.current;
    if (!input) return;
    input.focus();
    input.select();
  }, [editingId]);

  useEffect(() => {
    if (!editingId) return;
    const activeId = editingId;

    function onPointerDown(event: PointerEvent) {
      if (renamingIdRef.current === activeId) return;
      const input = renameInputRef.current;
      if (
        input &&
        event.target instanceof Node &&
        input.contains(event.target)
      ) {
        return;
      }
      cancelRename(activeId);
    }

    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [editingId]);

  async function onCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (creatingRef.current) return;
    creatingRef.current = true;
    setCreateError(null);
    setCreating(true);
    try {
      const result = await createKitchen(newName, messages);
      if (!result.ok) {
        setCreateError(result.error);
        return;
      }
      setNewName("");
    } finally {
      creatingRef.current = false;
      setCreating(false);
    }
  }

  function startRename(kitchen: KitchenItem) {
    if (renamingId || openingId) return;
    setRenameErrors((prev) => {
      const next = { ...prev };
      delete next[kitchen.id];
      return next;
    });
    setRenameDrafts((prev) => ({ ...prev, [kitchen.id]: kitchen.name }));
    setEditingId(kitchen.id);
  }

  function cancelRename(kitchenId: string) {
    if (renamingIdRef.current === kitchenId) return;
    setEditingId((current) => (current === kitchenId ? null : current));
    setRenameDrafts((prev) => {
      const next = { ...prev };
      delete next[kitchenId];
      return next;
    });
    setRenameErrors((prev) => {
      const next = { ...prev };
      delete next[kitchenId];
      return next;
    });
  }

  async function commitRename(kitchen: KitchenItem) {
    if (renamingIdRef.current === kitchen.id) return;
    const draft = (renameDrafts[kitchen.id] ?? kitchen.name).trim();
    if (draft.length === 0) {
      setRenameErrors((prev) => ({ ...prev, [kitchen.id]: t.errorInvalidName }));
      return;
    }
    if (draft === kitchen.name) {
      cancelRename(kitchen.id);
      return;
    }
    setRenameErrors((prev) => {
      const next = { ...prev };
      delete next[kitchen.id];
      return next;
    });
    renamingIdRef.current = kitchen.id;
    setRenamingId(kitchen.id);
    try {
      const result = await renameKitchen(kitchen.id, draft, messages);
      if (!result.ok) {
        setRenameErrors((prev) => ({ ...prev, [kitchen.id]: result.error }));
        return;
      }
      setEditingId((current) => (current === kitchen.id ? null : current));
      setRenameDrafts((prev) => {
        const next = { ...prev };
        delete next[kitchen.id];
        return next;
      });
    } finally {
      renamingIdRef.current = null;
      setRenamingId(null);
    }
  }

  function onRenameKeyDown(
    event: KeyboardEvent<HTMLInputElement>,
    kitchen: KitchenItem,
  ) {
    if (event.key === "Enter") {
      event.preventDefault();
      void commitRename(kitchen);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      cancelRename(kitchen.id);
    }
  }

  function showDeleteConfirm(kitchenId: string) {
    setDeleteConfirmId(kitchenId);
    setOpenMenuId(null);
  }

  function cancelDeleteConfirm() {
    setDeleteConfirmId(null);
  }

  async function confirmDelete(kitchen: KitchenItem) {
    if (deletingId === kitchen.id || openingId || editingId) return;
    setDeletingId(kitchen.id);
    try {
      const result = await deleteKitchen(kitchen.id, messages);
      if (!result.ok) {
        setCreateError(result.error);
        return;
      }
      setDeleteConfirmId(null);
    } finally {
      setDeletingId(null);
    }
  }

  async function openKitchen(kitchen: KitchenItem) {
    if (openingId || editingId) return;
    setOpeningId(kitchen.id);
    try {
      const result = await setLastOpenedKitchen(kitchen.id, messages);
      if (!result.ok) {
        setCreateError(result.error);
        return;
      }
      router.push(`/kitchens/${encodeURIComponent(kitchen.id)}`);
    } finally {
      setOpeningId(null);
    }
  }

  async function onArchive(kitchen: KitchenItem) {
    if (archivingId) return;
    setArchivingId(kitchen.id);
    setOpenMenuId(null);
    try {
      const result = await archiveKitchen(kitchen.id, messages);
      if (!result.ok) {
        setArchiveActionError(result.error);
      } else {
        setArchiveActionError(null);
      }
      // archiveKitchen already removes the kitchen from the shared membership
      // store on success — useMembershipKitchens() re-renders this row away.
    } finally {
      setArchivingId(null);
    }
  }

  async function onUnarchive(kitchen: KitchenItem) {
    if (archivingId) return;
    setArchivingId(kitchen.id);
    setOpenMenuId(null);
    try {
      const result = await unarchiveKitchen(kitchen.id, messages);
      if (!result.ok) {
        setArchiveActionError(result.error);
        return;
      }
      setArchiveActionError(null);
      setArchivedKitchens((prev) => prev.filter((item) => item.id !== kitchen.id));
      patchMembershipKitchens((prev) =>
        prev.some((item) => item.id === kitchen.id)
          ? prev
          : [...prev, { ...kitchen, is_archived: false }],
      );
    } finally {
      setArchivingId(null);
    }
  }

  async function onHide(kitchen: KitchenItem) {
    if (archivingId) return;
    setArchivingId(kitchen.id);
    setOpenMenuId(null);
    try {
      const result = await hideKitchen(kitchen.id, messages);
      if (!result.ok) {
        setArchiveActionError(result.error);
      } else {
        setArchiveActionError(null);
      }
      // hideKitchen already removes the kitchen from the shared membership
      // store on success — useMembershipKitchens() re-renders this row away.
    } finally {
      setArchivingId(null);
    }
  }

  async function onUnhide(kitchen: KitchenItem) {
    if (archivingId) return;
    setArchivingId(kitchen.id);
    setOpenMenuId(null);
    try {
      const result = await unhideKitchen(kitchen.id, messages);
      if (!result.ok) {
        setArchiveActionError(result.error);
        return;
      }
      setArchiveActionError(null);
      setArchivedKitchens((prev) => prev.filter((item) => item.id !== kitchen.id));
      patchMembershipKitchens((prev) =>
        prev.some((item) => item.id === kitchen.id) ? prev : [...prev, kitchen],
      );
    } finally {
      setArchivingId(null);
    }
  }

  const anyOpening = openingId !== null;

  const startInvite = useCallback((kitchenId: string) => {
    setInvitingKitchenId(kitchenId);
    setOpenMenuId(null);
  }, []);

  function renderKitchenRow(kitchen: KitchenItem) {
    const isOwner = kitchen.owner_id === currentUserId;
    const isEditing = editingId === kitchen.id;
    const draft = renameDrafts[kitchen.id] ?? kitchen.name;
    const faceProps = {
      kitchen,
      currentUserId,
      isOwner,
      memberBadge: t.memberBadge,
      ownerBadge: t.ownerBadge,
    };
    return (
      <>
        <div className={styles.cardShell}>
          {isEditing ? (
            <div className={styles.cardBody}>
              <KitchenCardFace
                {...faceProps}
                title={
                  <GhostTextField
                    ref={renameInputRef}
                    className="font-[650] text-[1.05rem] leading-[1.3]"
                    type="text"
                    value={draft}
                    placeholder={kitchen.name}
                    aria-label={t.renameAria}
                    onChange={(e) =>
                      setRenameDrafts((prev) => ({
                        ...prev,
                        [kitchen.id]: e.target.value,
                      }))
                    }
                    onBlur={() => cancelRename(kitchen.id)}
                    onKeyDown={(e) => onRenameKeyDown(e, kitchen)}
                    maxLength={200}
                    autoComplete="off"
                    disabled={renamingId === kitchen.id}
                  />
                }
              />
            </div>
          ) : (
            <>
              <button
                type="button"
                className={styles.cardButton}
                onClick={() => void openKitchen(kitchen)}
                disabled={anyOpening}
                aria-label={`${t.openLink}: ${kitchen.name}`}
              >
                <KitchenCardFace
                  {...faceProps}
                  title={<span className={styles.listName}>{kitchen.name}</span>}
                />
              </button>
              {isOwner ? (
                <div className={styles.menuCol}>
                  <IconButtonPopup
                    panelClassName={
                      deleteConfirmId === kitchen.id
                        ? styles.confirmPanel
                        : styles.menuPanel
                    }
                    panelRole={
                      deleteConfirmId === kitchen.id ? "alertdialog" : "menu"
                    }
                    open={openMenuId === kitchen.id || deleteConfirmId === kitchen.id}
                    onOpenChange={(next) => {
                      if (next) {
                        setOpenMenuId(kitchen.id);
                        setDeleteConfirmId(null);
                      } else {
                        setOpenMenuId((current) =>
                          current === kitchen.id ? null : current,
                        );
                        setDeleteConfirmId((current) =>
                          current === kitchen.id ? null : current,
                        );
                      }
                    }}
                    button={
                      <IconButton
                        type="button"
                        variant="muted"
                        className={styles.renameIcon}
                        label={t.menuAria}
                        disabled={anyOpening || renamingId !== null}
                        icon={<DotsIcon />}
                      />
                    }
                  >
                    {deleteConfirmId === kitchen.id ? (
                      <>
                        <p className={styles.confirmText}>{t.deleteConfirm}</p>
                        <div className={styles.confirmActions}>
                          <GhostButton
                            onClick={cancelDeleteConfirm}
                            disabled={deletingId !== null}
                          >
                            {t.deleteCancel}
                          </GhostButton>
                          <button
                            type="button"
                            className={`${styles.primary} ${styles.primaryDanger}`}
                            onClick={() => void confirmDelete(kitchen)}
                            disabled={deletingId !== null}
                          >
                            {deletingId === kitchen.id
                              ? t.deletingAction
                              : t.deleteAction}
                          </button>
                        </div>
                      </>
                    ) : showArchived ? (
                      <IconButtonPopupItem
                        onClick={() => void onUnarchive(kitchen)}
                        disabled={anyOpening || archivingId !== null}
                      >
                        <span className="flex items-center gap-4">
                          <ArchiveToggleIcon active className="h-4 w-4 shrink-0" />
                          {t.kitchensUnarchive}
                        </span>
                      </IconButtonPopupItem>
                    ) : (
                      <>
                        <IconButtonPopupItem
                          onClick={() => startInvite(kitchen.id)}
                          disabled={anyOpening}
                        >
                          <span className="flex items-center gap-4">
                            <UsersIcon className="h-4 w-4 shrink-0" />
                            {t.mobileInviteAria}
                          </span>
                        </IconButtonPopupItem>
                        <IconButtonPopupItem
                          onClick={() => startRename(kitchen)}
                          disabled={anyOpening || renamingId !== null}
                        >
                          <span className="flex items-center gap-4">
                            <PencilIcon className="h-4 w-4 shrink-0" />
                            {t.renameLabel}
                          </span>
                        </IconButtonPopupItem>
                        <IconButtonPopupItem
                          danger
                          stayOpen
                          onClick={() => showDeleteConfirm(kitchen.id)}
                          disabled={anyOpening || deletingId !== null}
                        >
                          <span className="flex items-center gap-4">
                            <TrashIcon className="h-4 w-4 shrink-0" />
                            {t.deleteAria}
                          </span>
                        </IconButtonPopupItem>
                        <IconButtonPopupItem
                          onClick={() => void onArchive(kitchen)}
                          disabled={anyOpening || archivingId !== null}
                        >
                          <span className="flex items-center gap-4">
                            <ArchiveToggleIcon className="h-4 w-4 shrink-0" />
                            {t.kitchensArchive}
                          </span>
                        </IconButtonPopupItem>
                      </>
                    )}
                  </IconButtonPopup>
                </div>
              ) : (
                <div className={styles.menuCol}>
                  <IconButtonPopup
                    panelClassName={styles.menuPanel}
                    panelRole="menu"
                    open={openMenuId === kitchen.id}
                    onOpenChange={(next) => {
                      setOpenMenuId(next ? kitchen.id : null);
                    }}
                    button={
                      <IconButton
                        type="button"
                        variant="muted"
                        className={styles.renameIcon}
                        label={t.menuAria}
                        disabled={anyOpening}
                        icon={<DotsIcon />}
                      />
                    }
                  >
                    {showArchived ? (
                      <IconButtonPopupItem
                        onClick={() => void onUnhide(kitchen)}
                        disabled={anyOpening || archivingId !== null}
                      >
                        <span className="flex items-center gap-4">
                          <ArchiveToggleIcon active className="h-4 w-4 shrink-0" />
                          {t.kitchensUnarchive}
                        </span>
                      </IconButtonPopupItem>
                    ) : (
                      <IconButtonPopupItem
                        onClick={() => void onHide(kitchen)}
                        disabled={anyOpening || archivingId !== null}
                      >
                        <span className="flex items-center gap-4">
                          <ArchiveToggleIcon className="h-4 w-4 shrink-0" />
                          {t.kitchensArchive}
                        </span>
                      </IconButtonPopupItem>
                    )}
                  </IconButtonPopup>
                </div>
              )}
            </>
          )}
        </div>
        {renameErrors[kitchen.id] ? (
          <p className={`${styles.error} ${styles.cardError}`} role="alert">
            {renameErrors[kitchen.id]}
          </p>
        ) : null}
      </>
    );
  }

  return (
    <>
      {archiveActionError ? (
        <p className={styles.error} role="alert">
          {archiveActionError}
        </p>
      ) : null}
      <StackedListPanel
        wrapperClassName={styles.panel}
        input={
          showArchived ? null : (
            <form className="flex w-full flex-col" onSubmit={onCreate}>
              <div className="flex items-stretch gap-2">
                <GhostInput
                  wrapperClassName="flex-1"
                  id={createNameId}
                  aria-label={t.createLabel}
                  type="text"
                  name="name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  maxLength={200}
                  autoComplete="off"
                  disabled={creating}
                  placeholder={t.createLabel}
                  trailing={
                    <IconButton
                      className="h-7 w-7 shrink-0 !p-0 !rounded-[4px]"
                      type="submit"
                      disabled={!canCreate}
                      label={creating ? t.creating : t.createSubmit}
                      icon={<PlusIcon />}
                    />
                  }
                />
              </div>
              {createError ? (
                <p className={styles.error} role="alert">
                  {createError}
                </p>
              ) : null}
            </form>
          )
        }
        items={kitchens}
        itemKey={(kitchen) => kitchen.id}
        itemClassName={styles.row}
        listClassName={styles.list}
        loading={showArchived && archivedLoading}
        loadingContent={<ArchivedKitchensSkeleton />}
        error={showArchived ? archivedLoadError : null}
        errorClassName={styles.error}
        emptyLabel={showArchived ? t.kitchensArchivedEmpty : t.emptyHint}
        emptyClassName={styles.copy}
        renderItem={renderKitchenRow}
      />

      {invitingKitchenId ? (
        <Sheet
          open={invitingKitchenId !== null}
          title={t.inviteTitle}
          closeLabel={t.mobileSheetClose}
          onClose={closeInviteSheet}
          body={
            <InviteForm
              kitchenId={invitingKitchenId}
              messages={messages}
              reserveErrorHeight
              hideBorder
            />
          }
        />
      ) : null}
    </>
  );
}
