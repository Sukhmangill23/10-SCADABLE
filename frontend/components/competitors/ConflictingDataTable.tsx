import type { DataConflict } from "@/lib/api";
import styles from "./CompetitorProfile.module.css";

type Props = {
  conflicts: DataConflict[];
};

function ClaimCell({
  text,
  sourceLabel,
  sourceUrl,
}: {
  text: string;
  sourceLabel: string;
  sourceUrl?: string;
}) {
  const source = sourceUrl ? (
    <a href={sourceUrl} target="_blank" rel="noreferrer">
      {sourceLabel}
    </a>
  ) : (
    sourceLabel
  );

  return (
    <>
      {text} <span className={styles.conflictSource}>({source})</span>
    </>
  );
}

/** Renders only when the parent passes a non-empty conflicts list. */
export function ConflictingDataTable({ conflicts }: Props) {
  if (conflicts.length === 0) return null;

  return (
    <section className={styles.card} aria-labelledby="conflicting-data-heading">
      <h2 id="conflicting-data-heading">Conflicting data</h2>
      <div className={styles.conflictTableWrap}>
        <table className={styles.conflictTable}>
          <thead>
            <tr>
              <th scope="col">Claim</th>
              <th scope="col">Conflicts with</th>
            </tr>
          </thead>
          <tbody>
            {conflicts.map((row) => (
              <tr key={row.id}>
                <td>
                  <ClaimCell
                    text={row.claim.text}
                    sourceLabel={row.claim.sourceLabel}
                    sourceUrl={row.claim.sourceUrl}
                  />
                </td>
                <td>
                  <ClaimCell
                    text={row.conflictsWith.text}
                    sourceLabel={row.conflictsWith.sourceLabel}
                    sourceUrl={row.conflictsWith.sourceUrl}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
