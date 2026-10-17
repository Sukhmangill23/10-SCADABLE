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
  const [sources, setSources] = useState<string[]>([""]);
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
    setSources([""]);
    setFormError(null);
    mutation.reset();
    onClose();
  }

  function updateSource(index: number, value: string) {
    setSources((prev) => prev.map((s, i) => (i === index ? value : s)));
  }

  function addSource() {
    setSources((prev) => [...prev, ""]);
  }

  function removeSource(index: number) {
    setSources((prev) => (prev.length <= 1 ? prev : prev.filter((_, i) => i !== index)));
  }

  function handleSubmit() {
    setFormError(null);
    const trimmedName = name.trim();
    const dataSources = sources.map((s) => s.trim()).filter(Boolean);

    if (!trimmedName) {
      setFormError("Company name is required.");
      return;
    }
    if (!dataSources.length) {
      setFormError("Add at least one data source.");
      return;
    }

    mutation.mutate({ name: trimmedName, dataSources });
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
            <p>We&apos;ll queue this company for automated research across sources.</p>

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
              <span className={styles.fieldLabel} id="add-sources-label">
                Data sources
              </span>
              {sources.map((source, index) => (
                <div key={index} className={styles.sourceRow}>
                  <input
                    type="text"
                    placeholder={
                      index === 0
                        ? "e.g. acme.example"
                        : "e.g. acme.example/careers"
                    }
                    value={source}
                    onChange={(e) => updateSource(index, e.target.value)}
                    disabled={mutation.isPending}
                    aria-labelledby="add-sources-label"
                  />
                  <button
                    type="button"
                    className={styles.removeSource}
                    aria-label={`Remove data source ${index + 1}`}
                    disabled={sources.length <= 1 || mutation.isPending}
                    onClick={() => removeSource(index)}
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                type="button"
                className={styles.addSource}
                onClick={addSource}
                disabled={mutation.isPending}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
                  <path d="M12 5v14M5 12h14" strokeLinecap="round" />
                </svg>
                Add data source
              </button>
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
