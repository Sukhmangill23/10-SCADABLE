import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Button.module.css";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "danger";
  children: ReactNode;
};

export function Button({
  variant = "primary",
  className,
  children,
  ...props
}: Props) {
  const classes = [
    styles.btn,
    variant === "secondary" ? styles.secondary : "",
    variant === "danger" ? styles.danger : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button type="button" className={classes} {...props}>
      {children}
    </button>
  );
}
