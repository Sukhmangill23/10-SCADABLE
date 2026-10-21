import styles from "./PlaceholderPanel.module.css";

type Props = {
  title: string;
  owner: string;
  description: string;
};

export function PlaceholderPanel({ title, owner, description }: Props) {
  return (
    <section className={styles.panel}>
      <p className={styles.owner}>{owner}</p>
      <h1 className={styles.title}>{title}</h1>
      <p className={styles.description}>{description}</p>
      <p className={styles.note}>
        Shared foundation is ready. Build this screen on a feature branch off{" "}
        <code>frontend/base</code>. Data should come from <code>lib/api</code>{" "}
        (mocks on by default).
      </p>
    </section>
  );
}
