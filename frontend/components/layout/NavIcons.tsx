/** Sidebar / brand icons — nav glyphs from the D1 prototype; brand mark is the SCADABLE logo. */

export function BrandMarkIcon() {
  return (
    // eslint-disable-next-line @next/next/no-img-element -- static public brand asset
    <img
      src="/scadable-logo.png"
      alt=""
      width={26}
      height={26}
      aria-hidden="true"
      draggable={false}
    />
  );
}

export function OverviewIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <rect x="4" y="4" width="6" height="6" rx="1" />
      <rect x="14" y="4" width="6" height="6" rx="1" />
      <rect x="4" y="14" width="6" height="6" rx="1" />
      <rect x="14" y="14" width="6" height="6" rx="1" />
    </svg>
  );
}

export function CompetitorsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <circle cx="9" cy="8" r="3" />
      <circle cx="17" cy="9" r="2.5" />
      <path
        d="M3.5 19c.5-3.2 2.4-5 5.5-5s5 1.8 5.5 5M14.5 14.5c3.2-.7 5.2.8 6 3.5"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function CompanyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path
        d="M5 20V5h9v15M14 10h5v10M8 8h3M8 12h3M8 16h3"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function RunsIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" aria-hidden="true">
      <path d="M4 6h16M4 12h16M4 18h10" strokeLinecap="round" />
      <circle cx="18" cy="18" r="2" />
    </svg>
  );
}
