"use client";

import { useEffect, useId, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { competitorsApi, type CompetitorSummary } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import styles from "./AddCompetitorModal.module.css";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function AddCompetitorModal({ open, onClose }: Props) {
  const titleId = useId();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [website, setWebsite] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: competitorsApi.createCompetitor,
    onSuccess: (result) => {
      // Update the list cache immediately so the new row shows without a filter toggle.
      queryClient.setQueryData<CompetitorSummary[]>(["competitors"], (prev) => {
        const existing = prev ?? [];
        if (existing.some((c) => c.id === result.competitor.id)) return existing;
        return [result.competitor, ...existing];
      });
      void queryClient.invalidateQueries({ queryKey: ["competitors"] });
      void queryClient.invalidateQueries({ queryKey: ["runs"] });
      setToast(`${result.competitor.name} added — queued for research`);
      resetAndClose();
    },
    onError: (err) => {
      setFormError(err instanceof Error ? err.message : "Could not add competitor.");
    },
  });

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  function resetAndClose() {
    setName("");
    setWebsite("");
    setFormError(null);
    mutation.reset();
    onClose();
  }

  function handleSubmit() {
    setFormError(null);
    const trimmedName = name.trim();
    const trimmedWebsite = website.trim();

    if (!trimmedName) {
      setFormError("Company name is required.");
      return;
    }
    if (!trimmedWebsite) {
      setFormError("Website link is required.");
      return;
    }

    // API still expects dataSources[]; backend stores the first as website.
    mutation.mutate({ name: trimmedName, dataSources: [trimmedWebsite] });
  }

  return (
    <>
      {open ? (
        <div
          className={styles.overlay}
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget && !mutation.isPending) resetAndClose();
          }}
        >
          <div
            className={styles.modal}
            role="dialog"
            aria-modal="true"
            aria-labelledby={titleId}
          >
            <h2 id={titleId}>Add a competitor</h2>
            <p>We&apos;ll queue this company for automated research from its website.</p>

            <div className={styles.field}>
              <label className={styles.fieldLabel} htmlFor="add-competitor-name">
                Company name
              </label>
              <input
                id="add-competitor-name"
                type="text"
                placeholder="e.g. Acme Analytics"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={mutation.isPending}
                autoFocus
              />
            </div>

            <div className={styles.field}>
              <label className={styles.fieldLabel} htmlFor="add-competitor-website">
                Website
              </label>
              <input
                id="add-competitor-website"
                type="text"
                placeholder="e.g. acme.example"
                value={website}
                onChange={(e) => setWebsite(e.target.value)}
                disabled={mutation.isPending}
              />
            </div>

            {formError ? <p className={styles.error}>{formError}</p> : null}

            <div className={styles.actions}>
              <Button
                variant="secondary"
                onClick={resetAndClose}
                disabled={mutation.isPending}
              >
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={mutation.isPending}>
                {mutation.isPending ? "Queuing…" : "Add & queue research"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {toast ? (
        <div className={styles.toast} role="status">
          {toast}
        </div>
      ) : null}
    </>
  );
}
