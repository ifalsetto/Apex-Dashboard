# Apex Dashboard v2 Beta Runbook

## Final decision

Use a clean beta checkout outside the older development folders:

```text
C:\FalseTech\Beta\Apex Dashboard
```

This prevents stale Vite cache paths, locked repair folders, old `node_modules`, and accidental local artifacts from breaking the beta run.

## Repo layout

```text
Apex-Dashboard/
  FalseTech-Apex-Trial/
    frontend/                 React + Vite dashboard
    backend/                  Cloudflare Worker Tracker proxy
  tools/
    beta/
      setup.ps1               clean clone/install/build
      run.ps1                 start local beta dashboard
      verify.ps1              typecheck/build/API checks
      sanitize-local.ps1      remove generated local artifacts
  docs/
    beta-runbook.md           local beta operating guide
    public-beta-runbook.md    public web deployment guide
    apex-dashboard-v2-map.md  frontend/backend route and feature map
    local-companion-plan.md   optional safe Windows companion design
    local-folder-map.md       local folder ownership guide
```

## First beta setup

From any PowerShell window:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
New-Item -ItemType Directory -Force "C:\FalseTech\Beta" | Out-Null
git clone https://github.com/ifalsetto/Apex-Dashboard.git "C:\FalseTech\Beta\Apex Dashboard"
cd "C:\FalseTech\Beta\Apex Dashboard"
.\tools\beta\setup.ps1
```

For a completely fresh rebuild:

```powershell
.\tools\beta\setup.ps1 -Fresh
```

## Run while playing Apex

```powershell
cd "C:\FalseTech\Beta\Apex Dashboard"
.\tools\beta\run.ps1
```

Open:

```text
http://localhost:5173/
```

Leave the PowerShell window open while Apex is running. Press `Ctrl+C` after the session.

The dashboard is safe to run while Apex Legends is open because the web app uses public profile data through the backend proxy. It does not bundle Apex Legends, read game memory, inject code, automate input, or bypass anti-cheat.

## Verify beta health

With the dashboard running in another terminal:

```powershell
cd "C:\FalseTech\Beta\Apex Dashboard"
.\tools\beta\verify.ps1
```

Expected frontend result:

```text
Local dashboard HTTP status: 200 OK
```

If the API returns `FORBIDDEN`, the frontend and proxy path are working; Tracker rejected the Worker key or account access.

## Sanitize local generated files

Preview only:

```powershell
.\tools\beta\sanitize-local.ps1
```

Apply cleanup:

```powershell
.\tools\beta\sanitize-local.ps1 -Apply
```

Remove local env too:

```powershell
.\tools\beta\sanitize-local.ps1 -Apply -IncludeLocalEnv
```

## Security rules

- Do not commit `.env.local`.
- Do not put Tracker/TRN API keys in the frontend.
- Keep `TRN_API_KEY` only in Cloudflare Worker secrets or the local Worker backend env used for authorized backend testing.
- Do not use a frontend API base URL env var. React must call relative `/api/apex/*` routes only, with local proxy/backend routing outside the browser bundle.
- Safe frontend env values are `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_REDIRECT_URI`, and `VITE_AUTH0_LOGOUT_URI`.
- Never commit `.env`, `.env.local`, secrets, API keys, tokens, `node_modules`, `dist`, `build`, cache folders, `.wrangler`, `.vite`, logs, or archives.
- Do not read Apex memory, inject into the game, hook anti-cheat, or bypass protections.
- Use safe external telemetry only: public API data, process state, local system metrics, network checks, and user-owned logs.

## Current beta API flow

```text
React dashboard on localhost:5173
  -> Vite /api proxy
  -> Cloudflare Worker
  -> Tracker API
```

## Known beta limitation

The live Apex match data is only as good as the external API refresh cycle. A later Windows companion service can add safe local session tracking without touching game memory or anti-cheat.

## Related beta docs

- `docs/public-beta-runbook.md`
- `docs/apex-dashboard-v2-map.md`
- `docs/local-companion-plan.md`
- `docs/local-folder-map.md`
