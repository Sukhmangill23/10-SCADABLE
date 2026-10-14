# Auth access (invite-only)

Live SWOT uses Clerk with **restricted sign-up**. Random people cannot create accounts on your deployed app. Access is by **invitation** (and optionally an allowlist in the Clerk dashboard).

## Current Clerk settings (development)

- Clerk application name: **LIVE SWOT**
- `sign_up_mode`: **restricted** (invite-only)
- Public self-serve sign-up: **off**
- App opens to **`/sign-in` only** — bare `/sign-up` redirects away (no “Access restricted” page)
- Invite acceptance UI only loads when the email link includes a Clerk ticket
- Dev bypass (**Go to dashboard**) still works locally for UI testing without an account

## How teammates / SCADABLE get access

### Option A — Clerk Dashboard (easiest)

1. Open [dashboard.clerk.com](https://dashboard.clerk.com/) → your **LIVE SWOT** app → **Users** → **Invitations**
2. Invite emails (team + SCADABLE)
3. They click the email link → finish account on `/sign-up` → then use **Sign in**

### Option B — Clerk CLI

From `frontend/`:

```bash
npx -y clerk@latest api /invitations --file scripts/invite-body.json --yes
```

Edit `scripts/invite-body.json` first:

```json
{
  "email_address": "person@example.com",
  "redirect_url": "http://localhost:3000/sign-up",
  "notify": true,
  "ignore_existing": true
}
```

For production, set `redirect_url` to your Vercel URL, e.g. `https://your-app.vercel.app/sign-up`.

### Option C — Create a user directly (no email invite)

```bash
npx -y clerk@latest users create --email person@example.com --password <temp-password> --yes
```

They can then sign in on `/sign-in`.

## App entry points

| Route | Role |
| --- | --- |
| `/sign-in` | Primary entry for allowed users |
| `/sign-up` | Used when accepting an **invitation** link |
| **Go to dashboard** | Local/dev UI bypass only — not real auth |

## Before SCADABLE production

1. Create/configure Clerk **production** instance
2. Keep sign-up mode **restricted**
3. Invite only SCADABLE + team emails
4. Put production keys in Vercel env vars
5. Turn off `ALLOW_DEV_DASHBOARD_BYPASS` (never set it in prod)
6. Optionally enable **Allowlist** in Clerk Dashboard → Restrictions if you want a hard email list in addition to invites

## Who to invite (fill in)

| Person | Email | Status |
| --- | --- | --- |
| Clerk owner | scadable.swot@gmail.com | invite as needed |
| FE partner | | |
| SCADABLE (Ali / team) | | |
| Other teammates | | |
