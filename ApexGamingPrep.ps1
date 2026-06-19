<#
.SYNOPSIS
  FalseTech Apex Gaming Prep / Restore

.DESCRIPTION
  Creates a lower-noise Windows gaming session for Apex Legends without
  disabling core Windows, networking, audio, Defender, firewall, launcher,
  or anti-cheat components.

  PREP MODE:
    - Saves current state to %TEMP%\FalseTechApexGamingPrepState.json
    - Closes safe nonessential user apps:
        browsers, cloud sync, remote access, Phone Link, Teams, Outlook,
        Overwolf, torrent clients, screen tools, companion launchers
    - Optional switches can close Discord, Steam WebHelper, G HUB, Razer apps
    - Optional switches can stop update/indexing services temporarily
    - Optional switch can disable active Bluetooth PAN adapters
    - Does NOT permanently disable services
    - Does NOT touch Apex, anti-cheat, Defender, Firewall, DHCP, DNS, audio, NVIDIA

  RESTORE MODE:
    - Restarts only services this script stopped
    - Re-enables only adapters this script disabled
    - Optionally relaunches apps it closed when executable paths were captured

.USAGE
  Safe prep:
    powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Prep

  Prep while keeping Steam and Discord alive:
    powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Prep

  Prep and close Discord too:
    powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Prep -CloseDiscord

  Prep with temporary update service stop. Run PowerShell as Administrator:
    powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Prep -StopUpdateServices

  Prep with router/network cleanup. Run as Administrator:
    powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Prep -DisableBluetoothPan -StopUpdateServices

  Restore:
    powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Restore

.NOTES
  Recommended: run your network monitor after Prep:
    python .\optimizer\network\network_monitor.py --target 192.168.1.1 --target 1.1.1.1 --target 8.8.8.8 --interval 5
#>

param(
    [ValidateSet("Prep","Restore","Status")]
    [string]$Mode = "Prep",

    [switch]$CloseDiscord,
    [switch]$CloseSteamWebHelper,
    [switch]$CloseGHub,
    [switch]$CloseRazer,

    [switch]$StopUpdateServices,
    [switch]$StopIndexing,
    [switch]$StopOfficeUpdate,
    [switch]$StopDeliveryOptimization,

    [switch]$DisableBluetoothPan,

    [switch]$NoRestartApps,
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"

$StatePath = Join-Path $env:TEMP "FalseTechApexGamingPrepState.json"
$LogRoot = Join-Path (Get-Location) "data\apex_gaming_prep"
$LogPath = Join-Path $LogRoot ("prep-log-{0}.txt" -f (Get-Date -Format "yyyyMMdd-HHmmss"))

$ProtectedProcessNames = @(
    "r5apex",
    "r5apex_dx12",
    "EasyAntiCheat",
    "EAAntiCheat.GameServiceLauncher",
    "EALauncher",
    "EADesktop",
    "EABackgroundService",
    "steam",
    "nvcontainer",
    "dwm",
    "explorer",
    "audiodg",
    "MsMpEng",
    "SecurityHealthService"
)

$ProtectedServiceNames = @(
    "Dhcp",
    "Dnscache",
    "BFE",
    "mpssvc",
    "WinDefend",
    "WdNisSvc",
    "Audiosrv",
    "AudioEndpointBuilder",
    "RpcSs",
    "RpcEptMapper",
    "EventLog",
    "PlugPlay",
    "Power",
    "Schedule",
    "NlaSvc",
    "nsi",
    "NVDisplay.ContainerLocalSystem",
    "EAAntiCheatService",
    "EasyAntiCheat",
    "EasyAntiCheat_EOS"
)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $line = "[{0}] [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Write-Host $line
    try {
        New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null
        Add-Content -Path $LogPath -Value $line -Encoding UTF8
    } catch {}
}

function Test-IsAdmin {
    try {
        $id = [Security.Principal.WindowsIdentity]::GetCurrent()
        $p  = New-Object Security.Principal.WindowsPrincipal($id)
        return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch {
        return $false
    }
}

function Get-ProcessRecords {
    param([string[]]$Names)

    $records = @()

    foreach ($name in ($Names | Select-Object -Unique)) {
        $items = Get-Process -Name $name -ErrorAction SilentlyContinue
        foreach ($p in $items) {
            $path = $null
            try { $path = $p.Path } catch { $path = $null }

            $records += [ordered]@{
                Id          = $p.Id
                ProcessName = $p.ProcessName
                Path        = $path
                WindowTitle = $p.MainWindowTitle
            }
        }
    }

    return $records
}

function Stop-SafeProcesses {
    param([string[]]$Names)

    $closed = @()

    foreach ($name in ($Names | Select-Object -Unique)) {
        if ($ProtectedProcessNames -contains $name) {
            Write-Log "Skipped protected process target: $name" "SAFE"
            continue
        }

        $processes = Get-Process -Name $name -ErrorAction SilentlyContinue
        foreach ($p in $processes) {
            $path = $null
            try { $path = $p.Path } catch { $path = $null }

            $closed += [ordered]@{
                Id          = $p.Id
                ProcessName = $p.ProcessName
                Path        = $path
                WindowTitle = $p.MainWindowTitle
            }

            if ($DryRun) {
                Write-Log "DryRun: would close process $($p.ProcessName) PID $($p.Id)"
            } else {
                try {
                    Stop-Process -Id $p.Id -Force -ErrorAction Stop
                    Write-Log "Closed process $($p.ProcessName) PID $($p.Id)"
                } catch {
                    Write-Log "Could not close process $($p.ProcessName) PID $($p.Id): $($_.Exception.Message)" "WARN"
                }
            }
        }
    }

    return $closed
}

function Stop-TemporaryServices {
    param([string[]]$Names)

    $stopped = @()

    foreach ($svcName in ($Names | Select-Object -Unique)) {
        if ($ProtectedServiceNames -contains $svcName) {
            Write-Log "Skipped protected service target: $svcName" "SAFE"
            continue
        }

        $svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
        if (-not $svc) {
            Write-Log "Service not found: $svcName" "WARN"
            continue
        }

        if ($svc.Status -eq "Running") {
            if ($DryRun) {
                Write-Log "DryRun: would stop service $svcName"
                $stopped += $svcName
            } else {
                try {
                    Stop-Service -Name $svcName -ErrorAction Stop
                    $stopped += $svcName
                    Write-Log "Stopped service $svcName temporarily"
                } catch {
                    Write-Log "Could not stop service ${svcName}: $($_.Exception.Message)" "WARN"
                }
            }
        } else {
            Write-Log "Service not running, no action: $svcName"
        }
    }

    return $stopped
}

function Disable-BluetoothPanAdapters {
    $disabled = @()

    try {
        $adapters = Get-NetAdapter -ErrorAction Stop |
            Where-Object {
                $_.InterfaceDescription -like "*Bluetooth*" -and
                $_.Status -eq "Up"
            }

        foreach ($a in $adapters) {
            if ($DryRun) {
                Write-Log "DryRun: would disable Bluetooth network adapter $($a.Name)"
                $disabled += $a.Name
            } else {
                try {
                    Disable-NetAdapter -Name $a.Name -Confirm:$false -ErrorAction Stop
                    $disabled += $a.Name
                    Write-Log "Disabled Bluetooth network adapter: $($a.Name)"
                } catch {
                    Write-Log "Could not disable adapter $($a.Name): $($_.Exception.Message)" "WARN"
                }
            }
        }
    } catch {
        Write-Log "Get-NetAdapter failed or is unavailable: $($_.Exception.Message)" "WARN"
    }

    return $disabled
}

function Show-Status {
    Write-Host ""
    Write-Host "FalseTech Apex Gaming Prep Status" -ForegroundColor Cyan
    Write-Host "State file: $StatePath"
    Write-Host "State exists: $(Test-Path $StatePath)"
    Write-Host "Admin: $(Test-IsAdmin)"
    Write-Host ""

    Write-Host "Top network-capable user processes currently running:" -ForegroundColor Cyan
    Get-Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessName -match "chrome|msedge|brave|firefox|discord|AnyDesk|OneDrive|GoogleDriveFS|Dropbox|steamwebhelper|PhoneExperienceHost|Teams|outlook|Overwolf|torrent|qbittorrent|utorrent" } |
        Select-Object ProcessName,Id,CPU,WS |
        Sort-Object ProcessName |
        Format-Table -AutoSize

    Write-Host ""
    Write-Host "Services of interest:" -ForegroundColor Cyan
    Get-Service -Name BITS,wuauserv,DoSvc,WSearch,ClickToRunSvc -ErrorAction SilentlyContinue |
        Select-Object Name,Status,StartType |
        Format-Table -AutoSize
}

if ($Mode -eq "Status") {
    Show-Status
    return
}

if ($Mode -eq "Prep") {
    $isAdmin = Test-IsAdmin

    Write-Log "Starting Apex gaming prep. Admin=$isAdmin DryRun=$DryRun"

    $targets = @(
        # Browsers
        "chrome",
        "msedge",
        "brave",
        "firefox",

        # Remote access
        "AnyDesk",

        # Cloud sync
        "OneDrive",
        "GoogleDriveFS",
        "Dropbox",

        # Windows companion/background apps
        "PhoneExperienceHost",
        "YourPhone",
        "MobileDevices",
        "CrossDeviceService",

        # Productivity/chat clients not needed in ranked
        "ms-teams",
        "Teams",
        "outlook",
        "olk",

        # Overlays / launch helpers / capture clutter
        "Overwolf",
        "OverwolfBrowser",
        "OverwolfLauncher",
        "SnippingTool",
        "ScreenClippingHost",

        # Torrent clients
        "qbittorrent",
        "utorrent",
        "BitTorrent",
        "Transmission",

        # Optional local AI client from startup
        "claude",
        "Claude"
    )

    if ($CloseDiscord) {
        $targets += @("Discord","DiscordCanary","DiscordPTB")
    }

    if ($CloseSteamWebHelper) {
        $targets += @("steamwebhelper")
    }

    if ($CloseGHub) {
        $targets += @("lghub","lghub_agent","lghub_updater")
    }

    if ($CloseRazer) {
        $targets += @("RazerAppEngine","RazerCentral","Razer Synapse Service Process","RazerAppEngine")
    }

    $state = [ordered]@{
        Timestamp        = (Get-Date).ToString("o")
        ComputerName     = $env:COMPUTERNAME
        UserName         = $env:USERNAME
        IsAdmin          = $isAdmin
        DryRun           = [bool]$DryRun
        ClosedProcesses  = @()
        StoppedServices  = @()
        DisabledAdapters = @()
        Notes            = @(
            "No protected core Windows, networking, audio, Defender, firewall, launcher, or anti-cheat service is targeted.",
            "Services are stopped only for the session and can be restored with -Mode Restore.",
            "Adapter changes only affect active Bluetooth PAN adapters when -DisableBluetoothPan is used."
        )
    }

    $state.ClosedProcesses = @(Stop-SafeProcesses -Names $targets)

    $serviceTargets = @()

    if ($StopUpdateServices) {
        $serviceTargets += @("BITS","wuauserv")
    }

    if ($StopIndexing) {
        $serviceTargets += @("WSearch")
    }

    if ($StopOfficeUpdate) {
        $serviceTargets += @("ClickToRunSvc")
    }

    if ($StopDeliveryOptimization) {
        $serviceTargets += @("DoSvc")
        Write-Log "StopDeliveryOptimization requested. This is more aggressive; use only for testing." "WARN"
    }

    if ($serviceTargets.Count -gt 0) {
        if ($isAdmin) {
            $state.StoppedServices = @(Stop-TemporaryServices -Names $serviceTargets)
        } else {
            Write-Log "Not Administrator; skipping service stops." "WARN"
        }
    }

    if ($DisableBluetoothPan) {
        if ($isAdmin) {
            $state.DisabledAdapters = @(Disable-BluetoothPanAdapters)
        } else {
            Write-Log "Not Administrator; skipping Bluetooth PAN adapter disable." "WARN"
        }
    }

    if (-not $DryRun) {
        try {
            $state | ConvertTo-Json -Depth 6 | Set-Content -Path $StatePath -Encoding UTF8
            Write-Log "State saved: $StatePath"
        } catch {
            Write-Log "Could not save state file: $($_.Exception.Message)" "ERROR"
        }
    }

    Write-Host ""
    Write-Host "Apex prep complete." -ForegroundColor Green
    Write-Host "Log: $LogPath"
    Write-Host "State: $StatePath"
    Write-Host ""
    Write-Host "Recommended next:"
    Write-Host "  1. Launch Steam/EA if needed."
    Write-Host "  2. Launch Apex."
    Write-Host "  3. Run network monitor for 1-5 minutes before ranked."
    Write-Host "  4. Restore after gaming: powershell -ExecutionPolicy Bypass -File .\ApexGamingPrep.ps1 -Mode Restore"
}

if ($Mode -eq "Restore") {
    Write-Log "Starting restore."

    if (-not (Test-Path $StatePath)) {
        Write-Host "No saved state found at $StatePath" -ForegroundColor Yellow
        return
    }

    try {
        $state = Get-Content $StatePath -Raw | ConvertFrom-Json
    } catch {
        Write-Host "Could not read saved state: $($_.Exception.Message)" -ForegroundColor Red
        return
    }

    $isAdmin = Test-IsAdmin

    if ($state.DisabledAdapters.Count -gt 0) {
        if ($isAdmin) {
            foreach ($name in $state.DisabledAdapters) {
                try {
                    Enable-NetAdapter -Name $name -Confirm:$false -ErrorAction Stop
                    Write-Log "Re-enabled adapter: $name"
                } catch {
                    Write-Log "Could not re-enable adapter ${name}: $($_.Exception.Message)" "WARN"
                }
            }
        } else {
            Write-Log "Not Administrator; cannot restore disabled adapters automatically." "WARN"
        }
    }

    if ($state.StoppedServices.Count -gt 0) {
        if ($isAdmin) {
            foreach ($svcName in $state.StoppedServices) {
                try {
                    Start-Service -Name $svcName -ErrorAction Stop
                    Write-Log "Restarted service: $svcName"
                } catch {
                    Write-Log "Could not restart service ${svcName}: $($_.Exception.Message)" "WARN"
                }
            }
        } else {
            Write-Log "Not Administrator; cannot restore services automatically." "WARN"
        }
    }

    if (-not $NoRestartApps) {
        foreach ($proc in $state.ClosedProcesses) {
            $path = $proc.Path
            if ($path -and (Test-Path $path)) {
                try {
                    Start-Process -FilePath $path -ErrorAction Stop | Out-Null
                    Write-Log "Restarted app: $($proc.ProcessName)"
                } catch {
                    Write-Log "Could not restart app $($proc.ProcessName): $($_.Exception.Message)" "WARN"
                }
            }
        }
    }

    try {
        Remove-Item $StatePath -Force -ErrorAction SilentlyContinue
    } catch {}

    Write-Host ""
    Write-Host "Restore complete." -ForegroundColor Green
}

