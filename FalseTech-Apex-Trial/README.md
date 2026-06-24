# FalseTech Apex Elite Dashboard — Trial Build

This is a full V1 trial build for company preview.

It is designed as:
- Apex-first companion app
- royal purple + gold brand system
- live player profiles
- live friend switching by username
- music lane on by default
- squads + creator identity surfaces
- default layout first
- creator unlock preview logic

## Project structure

- `frontend/` — Vite + React trial app
- `backend/` — Cloudflare Worker proxy for Tracker.gg

## Why the backend exists

The frontend never sends `TRN-Api-Key` directly.

Frontend calls only your proxy routes:
- `GET /api/apex/search?platform=origin&query=NotFalsetto`
- `GET /api/apex/profile/:platform/:player`
- `GET /api/apex/profile/:platform/:player/sessions`
- `GET /api/apex/profile/:platform/:player/segments/:segmentType`

The backend adds the Tracker key server-side.

## Steam note

The UI treats your PC profile as `Steam / EA (PC)`.
The backend still calls Tracker using the PC-compatible `origin` path.

## Frontend quick start

```bash
cd frontend
npm install
npm run dev
```

Default local frontend:
- `http://localhost:5173`

## Backend quick start

```bash
cd backend
npm install
npx wrangler secret put TRN_API_KEY
npm run dev
```

Default local worker:
- `http://127.0.0.1:8787`

## Local development recommendation

Run the backend first, then the frontend.

If needed during local testing, point frontend requests to the worker URL using a Vite proxy or deploy the worker and call that domain directly.

## Cloudflare deploy

1. Set the Tracker key secret:
```bash
npx wrangler secret put TRN_API_KEY
```

2. Update `backend/wrangler.toml` allowlist:
```toml
ALLOWED_ORIGINS = "https://your-frontend-domain.com,http://localhost:5173"
```

3. Deploy:
```bash
npm run deploy
```

## What is real vs preview-only in this build

### Real
- live player lookup
- live profile loading
- live sessions loading
- live legend segment loading
- friends by username
- automatic refresh behavior
- music hide/show rule

### Preview / investor-demo logic
- Spotify subscription verification
- song-added-to-playlist verification
- app-share verification
- Spotify-channel-share verification
- creator unlocks based on those actions

Those are intentionally shown as preview logic for the trial build.

## Best demo flow

1. Open the dashboard
2. Show the default layout identity
3. Search/open a live player
4. Switch to a saved friend username
5. Show legends / weapons / sessions panels
6. Show music lane default behavior
7. Show creator unlock preview controls
8. Explain how backend security keeps the Tracker key hidden

## Suggested next steps after the trial build

1. wire a real Spotify embed URL
2. add frontend proxy config for local dev
3. add true layout saving
4. wire actual Spotify/auth/share verification later
5. add compare-two-player mode
