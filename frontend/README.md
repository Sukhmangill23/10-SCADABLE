# Live SWOT — Frontend

Next.js (App Router) + TypeScript UI for SCADABLE Live SWOT.

This folder is the shared foundation on branch `frontend/base`. Feature work branches off that branch until `main` is open for merges.

## Ownership

| Person | Owns |
| --- | --- |
| **FE A** | Auth (Clerk), competitors list + profile, agent runs |
| **FE B** | SWOT overview, Our Company page, Vercel deployment (when ready) |

Do not edit each other’s feature folders without syncing.

## Branch workflow

```text
main (blocked for now)
  └── frontend/base          ← shared foundation (this branch)
        ├── feat/auth-clerk          (FE A — later)
        ├── feat/competitors         (FE A)
        ├── feat/runs                (FE A)
        ├── feat/swot-overview       (FE B)
        └── feat/company             (FE B)
```

1. Create your feature branch from `frontend/base`
2. Open PRs **into `frontend/base`** (not `main`) until `main` is unblocked
3. When `main` opens, open one PR: `frontend/base` → `main`

## Setup

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

App: [http://localhost:3000](http://localhost:3000)

Mocks are **on by default** (`NEXT_PUBLIC_USE_MOCKS` unset or not `"false"`).

## Docs

- [Frontend plan (MD)](./docs/Live-SWOT-Frontend-Plan.md)
- [Frontend plan (PDF)](./docs/Live-SWOT-Frontend-Plan.pdf)

## What’s in the base

- App shell (topbar + sidebar) and route stubs for all screens
- Design tokens from the mockup (`styles/tokens.css`)
- Shared UI starters: `Button`, `Pill`, `PlaceholderPanel`
- TanStack Query provider
- Typed API client + mock fixtures under `lib/api` and `lib/mocks`
- `.env.example` with API + future Clerk placeholders

## What’s intentionally not here yet

- **Vercel** — no project config beyond a normal Next.js app. When deploying, set the Vercel **Root Directory** to `frontend`.
- Real page UIs (list tables, SWOT grid, charts, run details) — build those on feature branches.

## Auth (Clerk)

Clerk is wired via `@clerk/nextjs`, `ClerkProvider`, and `proxy.ts` middleware.

- Unauthenticated users are sent to **`/sign-up`**
- Signed-in users land on `/competitors`
- Keys live in `.env.local` (created by `npx clerk init` — do not commit)
- Later you can claim the Clerk app with `npx clerk auth login`

**Go to dashboard (dev bypass):** Always shown on `/sign-up` and `/sign-in`. Works whether or not Clerk keys are configured — it sets a short-lived cookie and opens `/overview` without signing in. Available in `next dev`, or when `ALLOW_DEV_DASHBOARD_BYPASS=true`. Do not enable that env in real production.

```bash
npx -y clerk@latest doctor
```

## API modules

Import from `@/lib/api` (or the specific module):

- `competitorsApi.listCompetitors / getCompetitor / createCompetitor`
- `swotApi.getSwotOverview`
- `companyApi.getCompanyProfile`
- `runsApi.listRuns / getRun`

When the FastAPI backend is ready:

1. Set `NEXT_PUBLIC_API_URL`
2. Set `NEXT_PUBLIC_USE_MOCKS=false`
3. Ensure CORS allows the frontend origin

## Scripts

```bash
npm run dev      # local dev
npm run build    # production build
npm run start    # serve production build
npm run lint     # eslint
```
