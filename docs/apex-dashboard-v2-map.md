# Apex Dashboard v2 Map

## Product identity

Name: FalseTech Apex Dashboard v2 Beta.

Primary screen: local-first single-page Apex command center.

Theme: royal purple with gold and platinum accents.

Default profile: NotFalsetto.

## Frontend

Path:

```text
FalseTech-Apex-Trial/frontend
```

Main files:

```text
src/App.tsx
src/AuthPanel.tsx
src/styles.css
src/vite-env.d.ts
vite.config.ts
.env.example
```

Visible sections:

```text
Live Data Overview
Live Data
Music
Friends
Squads
Creator Tools
Performance
Legends
Weapons
Session Review
Settings
```

Key labels:

```text
Current Rank
Peak Rank
Main Legend
Best Loadout
Win Rate
Network
Performance
Match Notes
```

## Backend

Path:

```text
FalseTech-Apex-Trial/backend
```

Worker entry:

```text
src/index.ts
```

Public beta Worker:

```text
https://falsetech-apex-tracker-proxy.falsetech-andrew.workers.dev
```

Required routes:

```text
/health
/api/apex/search
/api/apex/profile/:platform/:player
/api/apex/profile/:platform/:player/sessions
/api/apex/profile/:platform/:player/segments/:segmentType
```

## Data and safety boundaries

Frontend calls use backend/proxy `/api` routes only. In local dev that is the relative Vite `/api` proxy. In production static builds it defaults to the public Cloudflare Worker, or to `VITE_API_BASE_URL` when that value is set to a safe backend/proxy base URL. Tracker credentials stay server-side in the Worker.

Allowed data:

- Public Tracker profile data.
- User-entered profile handles.
- Local browser settings such as saved friends, music visibility, and Spotify embed URL.
- Optional local companion session timestamps and network checks.

Not allowed:

- Bundling Apex Legends.
- Reading game memory.
- Injecting into game processes.
- Hooking or bypassing anti-cheat.
- Gameplay automation.
- Secrets in frontend code or committed env files.

## Local run

```powershell
cd "C:\FalseTech\Beta\Apex Dashboard\FalseTech-Apex-Trial\frontend"
npm install
npm run typecheck
npm run build
npm run dev
```

Open:

```text
http://localhost:5173/
```
