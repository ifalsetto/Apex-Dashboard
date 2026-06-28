# Optional Safe Local Companion Plan

This is a plan only. Do not build unsafe game integrations.

## Goal

Provide optional local-only context for a Windows player running Apex Legends while keeping the public web dashboard safe, deployable, and independent of local game files.

## Allowed companion behavior

- Detect whether `r5apex.exe` or `r5apex_dx12.exe` is running by process name only.
- Record session start and stop timestamps.
- Run ping and jitter checks against normal network targets.
- Write local JSON session logs owned by the user.
- Expose a local health endpoint such as `http://127.0.0.1:5273/health`.
- Optionally expose local read-only session summaries to the dashboard when the user explicitly runs the companion.

## Forbidden behavior

- No Apex Legends files bundled or uploaded.
- No game memory reading.
- No injection.
- No anti-cheat hooks.
- No anti-cheat bypass.
- No packet manipulation.
- No gameplay automation.
- No recoil scripts, macros, aim assistance, overlays, or competitive advantage tooling.
- No secrets in frontend code.

## Local endpoints

```text
GET http://127.0.0.1:5273/health
GET http://127.0.0.1:5273/session/current
GET http://127.0.0.1:5273/session/history
```

Responses should contain local-only metadata:

```json
{
  "ok": true,
  "apexRunning": true,
  "sessionStartedAt": "2026-06-27T00:00:00.000Z",
  "pingMs": 32,
  "jitterMs": 4
}
```

## Storage

Suggested local path:

```text
%LOCALAPPDATA%\FalseTech\Apex Dashboard\sessions
```

Suggested file shape:

```text
session-YYYYMMDD-HHMMSS.json
```

The public beta must continue working when the companion is absent.
