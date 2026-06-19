# Skill: FalseTech Apex Windows Process Hygiene

## Purpose

Optimize a Windows 11 workstation for Apex Legends by reducing background noise safely.

This skill does **not** disable core Windows components, anti-cheat, Defender, firewall, audio, DHCP, DNS, or launcher authentication. It focuses on closing nonessential user apps, pausing sync/update activity, disabling overlays, and measuring whether changes reduce ping, jitter, packet loss, and latency variance.

## When to use

Use before:
1. Ranked Apex sessions.
2. Testing new NVIDIA / Windows / router settings.
3. Running the FalseTech network monitor.
4. Troubleshooting jitter, latency variance, or packet timing inconsistency.

Do not use as a replacement for:
1. Driver troubleshooting.
2. Router/ISP diagnosis.
3. EA server outage checks.
4. Anti-cheat repair.

## Core rule

Do not kill random Windows services.

Only close what is:
1. Nonessential.
2. User-level.
3. Known to use overlay/sync/update/remote/network resources.
4. Observed to correlate with your network monitor spikes.

## Never touch during normal gaming optimization

Keep these alive:

- Apex Legends: `r5apex.exe`, `r5apex_dx12.exe`
- EA / Easy Anti-Cheat / Javelin anti-cheat
- Steam or EA App if used to launch Apex
- NVIDIA display/container services
- Windows Defender / Windows Security
- Windows Defender Firewall
- Base Filtering Engine
- DHCP Client
- DNS Client
- Network Store Interface Service
- Network List Service
- Network Location Awareness
- Windows Audio
- Windows Audio Endpoint Builder
- `audiodg.exe`
- Desktop Window Manager
- Explorer
- RPC / RPC Endpoint Mapper
- Plug and Play
- Power
- Task Scheduler
- Windows Event Log

## First apps to close

Close before queueing ranked:

- Chrome / Edge / Brave / Firefox
- AnyDesk
- Phone Link
- OneDrive
- Google Drive
- Dropbox
- Microsoft Teams
- Outlook
- Overwolf
- Snipping Tool / screen capture tools
- Torrent clients
- Claude desktop client if not needed
- Browser background tabs
- Active downloads

## Optional to keep

Keep only if needed:

- Discord voice
- G HUB for mouse/headset profiles
- Razer Synapse for mouse/headset profiles
- Steam if Apex is launched through Steam
- EA App if Apex is launched through EA App
- Armoury Crate / ROG services if controlling fan/performance mode

## Overlay rules

Disable if not actively needed:

- Discord overlay
- Steam overlay
- EA App overlay
- NVIDIA overlay / Instant Replay
- Overwolf overlays
- Browser video/audio streams
- Discord screen share

## Update/sync rules

Preferred GUI actions:

1. Pause Windows Update.
2. Pause OneDrive sync.
3. Pause Google Drive sync.
4. Stop Steam downloads.
5. Stop EA app downloads.
6. Stop torrent clients completely.

Temporary service actions:

- `BITS` may be stopped for the session if update/download activity is causing jitter.
- `wuauserv` may be stopped for the session if Windows Update is active.
- `WSearch` may be stopped if indexing causes disk spikes.
- `ClickToRunSvc` may be stopped if Office update/background activity appears.
- `DoSvc` / Delivery Optimization is more aggressive. Stop only for testing.

Never set these services to Disabled permanently as part of gaming prep.

## Bluetooth network rule

If using wired Ethernet and Bluetooth PAN is active:

- Disable only the Bluetooth **network adapter** for the session.
- Do not disable Bluetooth audio/support services if you use Bluetooth devices.

## Standard workflow

1. Check startup apps.
2. Close nonessential apps.
3. Pause sync/update/download activity.
4. Disable overlays.
5. Run `ApexGamingPrep.ps1 -Mode Prep`.
6. Run the network monitor:
   `python .\optimizer\network\network_monitor.py --target 192.168.1.1 --target 1.1.1.1 --target 8.8.8.8 --interval 5`
7. Queue Apex only if score stays stable.
8. Restore after session:
   `powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Restore`

## Success target

For AJ's wired Ethernet Apex setup:

- Ping: under 30ms preferred
- Jitter: under 5ms preferred
- Packet loss: 0%
- Latency variance: under 15ms
- Network score: 90+

## Failure decision tree

If `192.168.1.1` spikes:
- Problem is local PC/router/cable/adapter path.
- Check Ethernet cable, port, adapter power saving, Bluetooth PAN, background apps.

If `192.168.1.1` is stable but `1.1.1.1` / `8.8.8.8` spike:
- Problem is router WAN, ISP route, bufferbloat, or internet congestion.
- Check downloads/uploads, router QoS, ISP path.

If only one public target spikes:
- Likely route-specific. Compare Cloudflare vs Google.

If all targets spike and Task Manager network rises:
- Local app or sync process likely caused it.

If all targets spike and Task Manager network does not rise:
- Check router, ISP, cable, adapter, or external routing.

## Script included

Use `ApexGamingPrep.ps1`.

Recommended safe command:

```powershell
powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Prep
```

Admin command with update suppression and Bluetooth PAN cleanup:

```powershell
powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Prep -StopUpdateServices -DisableBluetoothPan
```

Restore:

```powershell
powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Restore
```
