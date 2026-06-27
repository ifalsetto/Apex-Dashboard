# Public Beta Runbook

Target: FalseTech Apex Dashboard v2 Beta.

This guide prepares the React dashboard and Cloudflare Worker proxy for a public beta URL. It does not bundle Apex Legends. Users install Apex separately through Steam or EA.

## Frontend deployment

Cloudflare Pages project path:

```text
FalseTech-Apex-Trial/frontend
```

Build command:

```powershell
npm install
npm run build
```

Build output:

```text
dist
```

Safe public frontend env values:

```text
VITE_API_BASE_URL=https://falsetech-apex-tracker-proxy.falsetech-andrew.workers.dev
VITE_AUTH0_DOMAIN=
VITE_AUTH0_CLIENT_ID=
VITE_AUTH0_REDIRECT_URI=
VITE_AUTH0_LOGOUT_URI=
```

Auth0 values are public application identifiers only. Do not put Tracker keys, Worker secrets, API tokens, or passwords in frontend env.

## Backend deployment

Cloudflare Worker project path:

```text
FalseTech-Apex-Trial/backend
```

Worker routes that must remain available:

```text
/health
/api/apex/search
/api/apex/profile/:platform/:player
/api/apex/profile/:platform/:player/sessions
/api/apex/profile/:platform/:player/segments/:segmentType
```

Required Worker secret:

```text
TRN_API_KEY
```

Optional Worker variable:

```text
ALLOWED_ORIGINS=https://your-public-beta-url.example
```

Deploy from the backend folder:

```powershell
cd "C:\FalseTech\Beta\Apex Dashboard\FalseTech-Apex-Trial\backend"
npm install
npx wrangler secret put TRN_API_KEY
npx wrangler deploy
```

## Public user flow

1. User opens the public beta URL.
2. User selects platform: Steam / EA, Xbox, or PlayStation.
3. User searches their Apex profile handle.
4. The frontend calls `/api/apex/*`.
5. The Cloudflare Worker calls Tracker with `TRN_API_KEY`.
6. The dashboard renders live stats, sessions, legends, weapons, friends, squads, music, creator tools, and settings.

If an API call returns `FORBIDDEN`, treat it as Tracker key, account, or upstream access, not a frontend routing failure.

## Never commit

Never commit `.env`, `.env.local`, API keys, tokens, passwords, `.dev.vars`, `.wrangler`, `node_modules`, `dist`, `build`, cache folders, logs, archives, local exports, or game files.

## Optional local companion

The public URL works without the optional Windows companion. A companion is only for local-only process state, session timestamps, ping/jitter checks, and local JSON session logs. It must not read Apex memory, inject code, hook anti-cheat, bypass protections, automate gameplay, or modify Apex Legends.
