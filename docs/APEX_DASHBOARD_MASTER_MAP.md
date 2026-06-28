# Apex Dashboard Master Project Map

This file is the single authority map for future Apex Dashboard v2 Codex work. When another note, old archive, or stale README conflicts with this file, follow this file first.

## Final Product Definition

FalseTech Apex Dashboard is a local-first Apex Legends command center. It is not a game mod, launcher, cheat, macro tool, anti-cheat bypass, or Apex Legends file bundle.

The current active product is Apex Dashboard v2, also referred to as Apex Operations. Its job is to give the user a reliable command center for public Apex profile data, sessions, legends, weapons, squads, music, creator tools, and performance context while preserving fallback beta data when live providers fail.

## Active Direction

The active direction is a tabbed command center, not a long accordion scroll page. Future UX work should preserve fast scanning, clear sections, and one visible work area per tab.

Required tabs:

- Command
- Live Data
- Friends
- Legends
- Weapons
- Sessions
- Squads
- Music
- Creator
- Performance
- Settings

API failures must not break the UI. Fallback beta data must always render.

## Active Repo Map

Active repo:

```text
C:\FalseTech\Projects\Apex-Dashboard
```

Primary v2 frontend:

```text
FalseTech-Apex-Trial/frontend
```

Primary v2 backend:

```text
FalseTech-Apex-Trial/backend
```

Legacy fallback app:

```text
apex_dashboard.py
pages/
```

Legacy Streamlit is preserved as fallback only. New Apex Dashboard v2 work belongs in `FalseTech-Apex-Trial/frontend`, `FalseTech-Apex-Trial/backend`, docs, tests, or Docker/CI files as required by the specific task.

## Recovered Archive Authority

Recovered archive folders are context, not active implementation authority. They may explain prior intent, naming, visual direction, or safety decisions, but do not copy files from them blindly and do not execute old archive scripts.

Archive/context examples:

- `Apex-Dashboard/`
- `Apex-HDR-SDR-Kit/`
- `ApexOps/`
- `Snapshots/`
- `TempBin/`
- legacy PowerShell helpers in the repo root

Use archive material only to recover intent. Rebuild current behavior in the v2 stack instead of moving old code forward wholesale.

## Locked Product Features

The v2 product must preserve these locked features:

- Local-first command center.
- Secure backend proxy for Tracker access.
- No direct frontend calls to Tracker or other external data APIs.
- Public profile lookup.
- Friend handle switching.
- Profile sessions.
- Legend segment data, with `legend` as the active segment target.
- Legends, weapons, sessions, squads, music, creator, performance, and settings views.
- Fallback beta data when live data is missing, denied, pending, or unavailable.
- Safe operation while Apex Legends is installed or running.

## Frontend Architecture

Active frontend stack:

- Vite
- React
- TypeScript
- Local browser storage for non-secret UI preferences
- Relative `/api/apex/*` calls only

Frontend rules:

- Frontend must never call Tracker directly.
- Frontend must never call external provider APIs directly.
- Frontend must never contain `TRN_API_KEY`, `TRACKER_API_KEY`, Tracker secrets, provider secrets, token URLs, or client secrets.
- Frontend must use local fallback data when API requests fail.
- Frontend route examples must stay relative, such as `/api/apex/profile/origin/NotFalsetto`.

## Backend Architecture

Active backend stack:

- Cloudflare Worker
- TypeScript
- Worker `env` bindings for secrets and runtime config
- `caches.default` for provider response caching

Required backend routes:

- `GET /health`
- `GET /api/apex/search?platform=origin&query=NotFalsetto`
- `GET /api/apex/profile/:platform/:player`
- `GET /api/apex/profile/:platform/:player/sessions`
- `GET /api/apex/profile/:platform/:player/segments/:segmentType`

Supported Apex platforms:

- `origin`
- `xbl`
- `psn`

Segment target:

- `legend`

Tracker Apex v2 route construction authority:

- Search maps to `/search?platform=:platform&query=:query`
- Profile maps to `/profile/:platform/:player`
- Profile sessions maps to `/profile/:platform/:player/sessions`
- Profile segments maps to `/profile/:platform/:player/segments/:segmentType`

Keep Apex platforms as `origin`, `xbl`, and `psn` even if copied Tracker segment docs mention `battlenet` or Overwatch. Treat that as a docs copy/paste inconsistency unless official Apex-specific docs say otherwise.

## Provider System

Provider chain:

```text
Controller -> Provider Layer -> Data Source
```

Provider priority:

1. Tracker Provider primary.
2. Mozambique / Apex Legends Status fallback.
3. Mock Provider failsafe.

Provider layer status:

- Tracker provider behavior exists through the current Worker proxy route construction.
- The full provider layer abstraction is not fully implemented.
- Future provider work must keep the controller-facing response shape stable.
- Fallback providers must never require frontend secrets.
- Mock Provider is a failsafe for UI continuity, not the preferred live source.

## Failure Handling Rules

Failure handling is a product requirement, not optional polish.

- API failures must not break the UI.
- Fallback beta data must always render.
- Missing `TRN_API_KEY` should report backend/provider status and keep the frontend usable.
- Pending or denied Tracker access should explain that live Tracker data is unavailable and keep local preview data visible.
- Upstream failures should report provider unavailability and keep local preview data visible.
- Provider-specific error details stay backend-side unless they are safe status messages.

## Cache Strategy

Current backend cache strategy:

- Search responses: short TTL.
- Profile responses: medium TTL.
- Sessions responses: medium TTL.
- Segments responses: medium TTL.
- Error responses should not become the long-lived source of truth.
- Cache keys must include the route and normalized platform/player/query/segment values.

Current Worker implementation uses these TTL targets:

- `search`: 45 seconds
- `profile`: 90 seconds
- `sessions`: 90 seconds
- `segments`: 120 seconds

Future provider work may refine these values, but must preserve quick recovery from provider failures and must not cache secrets.

## Docker Map

Active local runtime:

- Docker Compose local runtime.
- `backend` service builds `FalseTech-Apex-Trial/backend`.
- `frontend` service builds `FalseTech-Apex-Trial/frontend`.
- `apex-dashboard` service preserves legacy Streamlit fallback only.

Default ports:

- Frontend: `5173`
- Backend: `8787`
- Legacy Streamlit fallback: `8501`

Compose ownership:

- Frontend container serves the React app and proxies `/api` to backend.
- Backend container runs the Worker local runtime and owns Tracker access.
- Legacy Streamlit container exists for fallback compatibility, not as the v2 primary app.

## Secrets And Environment Boundary

Backend owns all secrets.

Secret rules:

- No API keys in frontend.
- No secrets committed.
- Do not edit `.env`, `.env.local`, `.dev.vars`, `.streamlit/secrets.toml`, or secret files unless a task explicitly requires a safe secret-handling change.
- `TRN_API_KEY` is the Apex Dashboard v2 Worker backend variable.
- `TRACKER_API_KEY` is legacy Streamlit compatibility only.
- Frontend Vite env values may only be public app identifiers such as Auth0 domain/client ID/redirect/logout values.
- Do not add Tracker client secrets, token URLs, authorization URLs, scopes, or redirect URIs to React.

## Dev Ops Hidden Panel

The Dev Ops hidden panel is an operator-only concept for future diagnostics. It is not a place for secrets and must not expose provider keys, raw tokens, `.env` contents, or sensitive machine data.

Allowed Dev Ops panel content:

- Build/runtime status.
- Provider health summaries.
- Cache status summaries.
- Safe route check results.
- Docker service status summaries.
- Non-secret version and branch metadata.

Disallowed Dev Ops panel content:

- API keys.
- OAuth client secrets.
- Raw access or refresh tokens.
- Full environment dumps.
- Game memory, process injection, or anti-cheat bypass controls.

## Safety And Legal Boundaries

Hard boundaries:

- No Apex game files bundled.
- No memory reading.
- No process injection.
- No anti-cheat hooks.
- No anti-cheat bypass.
- No gameplay automation.
- No recoil scripts, macros, or aim assistance.
- No secrets committed.

Allowed scope:

- Public API data.
- User-entered profile handles.
- Local browser UI preferences.
- Safe performance/network context.
- Optional future local companion telemetry that does not inspect or alter Apex Legends.

## Current Known State

Current active app:

- Apex Dashboard v2 / Apex Operations.
- Vite + React frontend.
- Cloudflare Worker backend.
- Docker Compose local runtime.
- Legacy Streamlit preserved as fallback only.

Current known blockers and work queue items:

- Tracker API key pending approval.
- Local Docker/workerd TLS certificate trust issue.
- Dashboard buttons/UX need tabbed refactor.
- Provider layer not fully implemented.

These blockers are planning authority for future PRs. Before closing any blocker, verify it against the current branch and live runtime because some work may already be in progress in another PR.

## Build Order

Recommended build order:

1. Preserve the safety and secret boundary.
2. Stabilize backend Docker TLS and local Worker runtime.
3. Keep backend routes aligned to the Tracker Apex v2 route map.
4. Maintain frontend fallback rendering.
5. Move UX toward the required tabbed command center.
6. Add the provider layer behind existing backend route contracts.
7. Update public beta docs after behavior is verified.
8. Keep legacy Streamlit fallback functional but do not make it the primary v2 surface.

## Validation Commands

Run from repo root unless a command states otherwise.

Frontend typecheck:

```powershell
cd "C:\FalseTech\Projects\Apex-Dashboard\FalseTech-Apex-Trial\frontend"
npm run typecheck
```

Frontend build:

```powershell
cd "C:\FalseTech\Projects\Apex-Dashboard\FalseTech-Apex-Trial\frontend"
npm run build
```

Frontend full check:

```powershell
cd "C:\FalseTech\Projects\Apex-Dashboard\FalseTech-Apex-Trial\frontend"
npm run check
```

Backend check:

```powershell
cd "C:\FalseTech\Projects\Apex-Dashboard\FalseTech-Apex-Trial\backend"
npm run check
```

Docker Compose config and build:

```powershell
cd "C:\FalseTech\Projects\Apex-Dashboard"
docker compose config
docker compose build backend frontend
```

Docker Compose runtime:

```powershell
cd "C:\FalseTech\Projects\Apex-Dashboard"
docker compose up -d backend frontend
docker compose ps
```

Backend `/health`:

```powershell
curl.exe -i "http://127.0.0.1:8787/health"
```

Backend search route:

```powershell
curl.exe -i "http://127.0.0.1:8787/api/apex/search?platform=origin&query=NotFalsetto"
```

Frontend HTTP 200:

```powershell
curl.exe -I "http://127.0.0.1:5173/"
```

TLS diagnostic from backend container:

```powershell
docker compose exec -T backend sh -lc 'node -e "fetch(\"https://public-api.tracker.gg\").then(r=>console.log(\"TLS OK HTTP\", r.status)).catch(e=>{console.error(e);process.exit(1)})"'
```

Stop runtime after validation:

```powershell
docker compose down --remove-orphans
```

## Next PR Queue

Recommended next PRs after this authority map:

1. Backend Docker TLS fix.
2. Tabbed command center UX.
3. Provider layer.
4. Pending Tracker fallback UI.
5. Public beta documentation.

Keep each PR focused. Do not combine provider abstraction, UX redesign, TLS repair, and public beta docs unless the user explicitly asks for a combined pass.

## What To Ignore From Old Archives

Ignore or treat as historical unless explicitly requested:

- Old archive app shells that duplicate the v2 frontend.
- Old PowerShell launch/repair scripts outside the current Docker/Vite/Worker path.
- Old Streamlit-first product direction, except fallback compatibility.
- Old copied OpenAPI experiments unless they are verified against current official docs.
- Old local machine exports, logs, caches, snapshots, and generated folders.
- Any archive material that implies direct frontend access to Tracker or frontend-held secrets.

Do not execute old archive scripts. Do not copy archive files blindly into the repo.

## Resume Command

Use this command when resuming future Apex Dashboard v2 work:

```text
Codex, read docs/APEX_DASHBOARD_MASTER_MAP.md first and treat it as the authority for Apex Dashboard v2. Then inspect the current branch and continue only within the requested scope.
```
